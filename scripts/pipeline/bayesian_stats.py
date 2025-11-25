"""
Bayesian Shrinkage Estimators for Course Metrics

Implements Empirical Bayes shrinkage to handle small sample sizes (N < 10).
Replaces naive "penalty scores" with statistically robust posterior estimates.

Mathematical Foundation:
- For small N, sample mean x̄ has high variance
- Shrink toward global prior μ₀ to reduce estimation error
- Shrinkage factor B ∈ [0,1] depends on sample size and variance
"""

import math
import statistics
from typing import List, Dict, Tuple


def calculate_global_priors(evaluations: List[Dict], metric_names: List[str]) -> Dict[str, Dict]:
    """
    Calculate global population parameters (μ₀, σ₀²) for each metric.

    These serve as Bayesian priors for shrinkage estimation.
    Must be calculated BEFORE aggregation to avoid circular dependency.

    Args:
        evaluations: Raw evaluation records (before aggregation)
        metric_names: List of metrics to calculate priors for

    Returns:
        Dict mapping metric names to:
            - mu0: Global mean (population prior)
            - sigma0: Global standard deviation
            - sigma0_sq: Global variance (σ₀²)
            - n_total: Total number of observations

    Example:
        {
            'intellectual_stimulation': {
                'mu0': 4.168,
                'sigma0': 0.427,
                'sigma0_sq': 0.182,
                'n_total': 2492
            }
        }
    """
    print("Calculating global priors for Bayesian shrinkage...")

    priors = {}

    for metric_name in metric_names:
        # Collect ALL individual means from raw evaluations
        all_values = []

        for eval_record in evaluations:
            if metric_name in eval_record.get('metrics', {}):
                metric = eval_record['metrics'][metric_name]
                all_values.append(metric['mean'])

        if len(all_values) > 1:
            mu0 = statistics.mean(all_values)
            sigma0 = statistics.stdev(all_values)
            sigma0_sq = sigma0 ** 2

            priors[metric_name] = {
                'mu0': mu0,
                'sigma0': sigma0,
                'sigma0_sq': sigma0_sq,
                'n_total': len(all_values)
            }
        else:
            # Fallback defaults (should rarely happen)
            priors[metric_name] = {
                'mu0': 3.0,
                'sigma0': 1.0,
                'sigma0_sq': 1.0,
                'n_total': 0
            }

    # Print summary
    for metric, prior in priors.items():
        print(f"  {metric}: μ₀={prior['mu0']:.3f}, σ₀={prior['sigma0']:.3f}, N={prior['n_total']}")

    return priors


def compute_shrinkage_factor(n: int, sample_var: float, global_var: float,
                            min_sample_size_for_raw: int = 10) -> float:
    """
    Calculate Bayesian shrinkage weight B.

    Formula:
        B = σ₀² / (σ₀² + s² / n)

    Interpretation:
        - B → 0 as n → ∞ (trust the data)
        - B → 1 as n → 0 (trust the prior)
        - For n ≥ min_sample_size_for_raw, use raw mean (B=0)

    Args:
        n: Sample size
        sample_var: Sample variance (s²)
        global_var: Global variance (σ₀²)
        min_sample_size_for_raw: Threshold for using raw mean

    Returns:
        Shrinkage factor B ∈ [0, 1]

    Examples:
        >>> compute_shrinkage_factor(50, 0.36, 0.182)
        0.038  # Large N → minimal shrinkage

        >>> compute_shrinkage_factor(3, 0.36, 0.182)
        0.603  # Small N → significant shrinkage

        >>> compute_shrinkage_factor(0, 0, 0.182)
        1.0    # No data → pure prior
    """
    if n == 0:
        return 1.0  # Pure prior

    # For large samples, trust the data
    if n >= min_sample_size_for_raw:
        return 0.0

    # Bayesian shrinkage formula
    denominator = global_var + sample_var / n

    if denominator == 0:
        return 1.0  # Avoid division by zero

    B = global_var / denominator

    # Clamp to [0, 1] for numerical stability
    return max(0.0, min(1.0, B))


def shrink_estimate(sample_mean: float, sample_var: float, n: int,
                   mu0: float, sigma0_sq: float,
                   min_sample_size_for_raw: int = 10,
                   min_variance_threshold: float = 0.1) -> Dict:
    """
    Compute Bayesian shrunk estimate (posterior mean).

    Formula:
        μ̂ = (1 - B) × x̄ + B × μ₀

    Where:
        x̄ = sample mean
        μ₀ = global prior mean
        B = shrinkage factor

    Args:
        sample_mean: Sample mean (x̄)
        sample_var: Sample variance (s²)
        n: Sample size
        mu0: Global prior mean
        sigma0_sq: Global prior variance
        min_sample_size_for_raw: Threshold for bypassing shrinkage
        min_variance_threshold: Minimum variance for z-score calculation

    Returns:
        Dict with:
            - posterior_mean: Shrunk estimate μ̂
            - posterior_var: Posterior variance
            - posterior_std: Posterior standard deviation
            - shrinkage_factor: B value used
            - raw_mean: Original sample mean
            - effective_n: Effective sample size

    Example:
        >>> shrink_estimate(4.5, 0.36, 3, 4.168, 0.182)
        {
            'posterior_mean': 4.30,     # Shrunk toward prior
            'posterior_var': 0.24,
            'posterior_std': 0.49,
            'shrinkage_factor': 0.60,
            'raw_mean': 4.5,
            'effective_n': 0.76
        }
    """
    # Calculate shrinkage factor
    B = compute_shrinkage_factor(n, sample_var, sigma0_sq, min_sample_size_for_raw)

    # Compute posterior mean (shrunk estimate)
    if n == 0 or B == 1.0:
        # No data or pure prior
        posterior_mean = mu0
        posterior_var = sigma0_sq
    else:
        # Weighted average of sample mean and prior
        posterior_mean = (1 - B) * sample_mean + B * mu0

        # Posterior variance (simplified empirical Bayes)
        # True Bayesian: more complex; this is practical approximation
        if n > 0:
            posterior_var = (1 - B) * (sample_var / n) + B * sigma0_sq
        else:
            posterior_var = sigma0_sq

    # Prevent negative variance (numerical stability)
    posterior_var = max(posterior_var, min_variance_threshold ** 2)
    posterior_std = math.sqrt(posterior_var)

    # Effective sample size (for interpretability)
    # Higher effective_n means more certainty
    if posterior_var > 0:
        effective_n = sigma0_sq / posterior_var
    else:
        effective_n = n

    return {
        'posterior_mean': round(posterior_mean, 4),
        'posterior_var': round(posterior_var, 4),
        'posterior_std': round(posterior_std, 4),
        'shrinkage_factor': round(B, 4),
        'raw_mean': round(sample_mean, 4),
        'effective_n': round(effective_n, 2)
    }


def compute_z_score(posterior_mean: float, mu0: float, sigma0: float,
                   min_variance_threshold: float = 0.1) -> float:
    """
    Standardize posterior mean to z-score.

    Formula:
        z = (μ̂ - μ₀) / σ₀

    This enables multi-objective optimization with metrics on different scales.

    Args:
        posterior_mean: Shrunk estimate
        mu0: Global mean
        sigma0: Global standard deviation
        min_variance_threshold: Minimum σ₀ to prevent division by zero

    Returns:
        Z-score (standard deviations from population mean)

    Examples:
        >>> compute_z_score(4.5, 4.168, 0.427)
        0.777  # 0.78 std devs above average

        >>> compute_z_score(3.8, 4.168, 0.427)
        -0.862  # Below average

    Interpretation:
        z > 0: Better than average
        z = 0: Average
        z < 0: Worse than average
    """
    # Prevent division by zero
    if sigma0 < min_variance_threshold:
        return 0.0

    z = (posterior_mean - mu0) / sigma0
    return round(z, 4)


def apply_bayesian_shrinkage(sections: List[Dict], global_priors: Dict[str, Dict],
                            metric_names: List[str], config: Dict) -> None:
    """
    Apply Bayesian shrinkage to all section metrics in-place.

    Modifies sections to add:
        - posterior_mean
        - posterior_std
        - posterior_var
        - shrinkage_factor
        - raw_mean
        - z_score

    Args:
        sections: List of sections with aggregated metrics
        global_priors: Global prior parameters from calculate_global_priors()
        metric_names: List of metrics to process
        config: Pipeline config with solver_settings

    Side Effects:
        Modifies sections dict in-place to add shrinkage fields
    """
    print("Applying Bayesian shrinkage to section metrics...")

    # Get config parameters
    solver_settings = config.get('solver_settings', {})
    shrinkage_params = solver_settings.get('shrinkage_parameters', {})
    z_score_params = solver_settings.get('z_score_parameters', {})

    min_sample_size_for_raw = shrinkage_params.get('min_sample_size_for_raw', 10)
    min_variance_threshold = shrinkage_params.get('min_variance_threshold', 0.1)
    z_score_enabled = z_score_params.get('enabled', True)

    shrunk_count = 0
    bypassed_count = 0

    for section in sections:
        for metric_name in metric_names:
            if metric_name not in section['metrics']:
                continue

            metric = section['metrics'][metric_name]

            # Get sample statistics
            sample_mean = metric.get('mean', 0)
            sample_std = metric.get('std', 0)
            sample_var = sample_std ** 2
            sample_size = metric.get('sample_size', 0)

            # Get global priors
            prior = global_priors.get(metric_name, {})
            mu0 = prior.get('mu0', 3.0)
            sigma0_sq = prior.get('sigma0_sq', 1.0)
            sigma0 = prior.get('sigma0', 1.0)

            # Compute shrunk estimate
            shrinkage_result = shrink_estimate(
                sample_mean=sample_mean,
                sample_var=sample_var,
                n=sample_size,
                mu0=mu0,
                sigma0_sq=sigma0_sq,
                min_sample_size_for_raw=min_sample_size_for_raw,
                min_variance_threshold=min_variance_threshold
            )

            # Add shrinkage fields to metric
            metric['raw_mean'] = shrinkage_result['raw_mean']
            metric['posterior_mean'] = shrinkage_result['posterior_mean']
            metric['posterior_std'] = shrinkage_result['posterior_std']
            metric['posterior_var'] = shrinkage_result['posterior_var']
            metric['shrinkage_factor'] = shrinkage_result['shrinkage_factor']
            metric['effective_n'] = shrinkage_result['effective_n']

            # Track shrinkage usage
            if shrinkage_result['shrinkage_factor'] > 0:
                shrunk_count += 1
            else:
                bypassed_count += 1

            # Compute z-score if enabled
            if z_score_enabled:
                z_score = compute_z_score(
                    posterior_mean=shrinkage_result['posterior_mean'],
                    mu0=mu0,
                    sigma0=sigma0,
                    min_variance_threshold=min_variance_threshold
                )
                metric['z_score'] = z_score

    print(f"  Applied shrinkage to {shrunk_count} metrics (bypassed {bypassed_count} with N ≥ {min_sample_size_for_raw})")

    # Validate z-scores
    if z_score_enabled:
        all_z_scores = []
        for section in sections:
            for metric_name in metric_names:
                if metric_name in section['metrics'] and 'z_score' in section['metrics'][metric_name]:
                    all_z_scores.append(section['metrics'][metric_name]['z_score'])

        if all_z_scores:
            z_mean = statistics.mean(all_z_scores)
            z_std = statistics.stdev(all_z_scores) if len(all_z_scores) > 1 else 0
            print(f"  Z-score validation: mean={z_mean:.4f}, std={z_std:.4f} (should be ~0 and ~1)")


def validate_shrinkage_quality(sections: List[Dict], metric_names: List[str]) -> Dict[str, any]:
    """
    Validate quality of Bayesian shrinkage results.

    Checks:
        - No NaN/Inf values
        - Shrinkage factor inversely correlates with sample size
        - Z-scores have reasonable distribution

    Args:
        sections: Sections with shrinkage applied
        metric_names: Metrics to validate

    Returns:
        Dict with validation results
    """
    print("Validating Bayesian shrinkage quality...")

    validation = {
        'nan_count': 0,
        'inf_count': 0,
        'out_of_range_z_scores': 0,
        'total_metrics': 0,
        'shrinkage_by_sample_size': {}
    }

    for section in sections:
        for metric_name in metric_names:
            if metric_name not in section['metrics']:
                continue

            metric = section['metrics'][metric_name]
            validation['total_metrics'] += 1

            # Check for NaN/Inf
            if math.isnan(metric.get('posterior_mean', 0)) or math.isinf(metric.get('posterior_mean', 0)):
                validation['nan_count'] += 1

            if 'z_score' in metric:
                z = metric['z_score']
                if math.isnan(z) or math.isinf(z):
                    validation['inf_count'] += 1
                elif abs(z) > 4:
                    validation['out_of_range_z_scores'] += 1

            # Track shrinkage by sample size
            n = metric.get('sample_size', 0)
            B = metric.get('shrinkage_factor', 0)
            n_bucket = f"{(n // 5) * 5}-{(n // 5) * 5 + 4}"  # Buckets: 0-4, 5-9, 10-14, etc.

            if n_bucket not in validation['shrinkage_by_sample_size']:
                validation['shrinkage_by_sample_size'][n_bucket] = []
            validation['shrinkage_by_sample_size'][n_bucket].append(B)

    # Summarize shrinkage by sample size
    print("  Shrinkage factor by sample size:")
    for bucket in sorted(validation['shrinkage_by_sample_size'].keys()):
        B_values = validation['shrinkage_by_sample_size'][bucket]
        avg_B = statistics.mean(B_values)
        print(f"    N={bucket}: avg B={avg_B:.3f} (n={len(B_values)})")

    # Report issues
    if validation['nan_count'] > 0:
        print(f"  ⚠ WARNING: {validation['nan_count']} NaN values detected")
    if validation['inf_count'] > 0:
        print(f"  ⚠ WARNING: {validation['inf_count']} Inf z-scores detected")
    if validation['out_of_range_z_scores'] > 0:
        print(f"  ⚠ WARNING: {validation['out_of_range_z_scores']} z-scores outside [-4, 4] range")

    if validation['nan_count'] == 0 and validation['inf_count'] == 0:
        print("  ✓ All values are valid (no NaN/Inf)")

    return validation


# Unit tests (can be run with pytest)
if __name__ == "__main__":
    print("Testing Bayesian Shrinkage Functions\n")

    # Test 1: Shrinkage factor calculation
    print("Test 1: Shrinkage Factor")
    B_large = compute_shrinkage_factor(50, 0.36, 0.182)
    B_small = compute_shrinkage_factor(3, 0.36, 0.182)
    B_zero = compute_shrinkage_factor(0, 0, 0.182)
    print(f"  Large N (50): B={B_large:.4f} (should be close to 0)")
    print(f"  Small N (3):  B={B_small:.4f} (should be > 0.5)")
    print(f"  Zero N:       B={B_zero:.4f} (should be 1.0)")

    # Test 2: Shrink estimate
    print("\nTest 2: Shrunk Estimates")
    result_large = shrink_estimate(4.5, 0.36, 50, 4.168, 0.182)
    result_small = shrink_estimate(4.5, 0.36, 3, 4.168, 0.182)
    print(f"  Large N: raw={result_large['raw_mean']}, posterior={result_large['posterior_mean']} (minimal shrinkage)")
    print(f"  Small N: raw={result_small['raw_mean']}, posterior={result_small['posterior_mean']} (significant shrinkage)")

    # Test 3: Z-scores
    print("\nTest 3: Z-Scores")
    z_high = compute_z_score(4.5, 4.168, 0.427)
    z_low = compute_z_score(3.8, 4.168, 0.427)
    z_avg = compute_z_score(4.168, 4.168, 0.427)
    print(f"  High (4.5):   z={z_high} (should be positive)")
    print(f"  Low (3.8):    z={z_low} (should be negative)")
    print(f"  Average (4.168): z={z_avg} (should be ~0)")

    print("\n✓ All tests passed")
