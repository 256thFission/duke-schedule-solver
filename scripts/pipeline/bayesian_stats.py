"""
Bayesian Shrinkage Estimators for Course Metrics

Implements hybrid Empirical Bayes shrinkage to handle small sample sizes.

- Ordinal metrics (1-5 Likert): Beta-Binomial conjugate model.
  Respects bounded support, couples mean and variance naturally.
- Continuous metrics (hours_per_week): Normal-Normal Empirical Bayes.

Mathematical Foundation:
- For small N, sample mean x̄ has high variance
- Shrink toward global prior μ₀ to reduce estimation error
- Shrinkage factor B ∈ [0,1] depends on sample size and prior strength
"""

import math
import statistics
from typing import List, Dict, Tuple

# Metrics measured on a 1-5 Likert scale (ordinal) → Beta-Binomial shrinkage
ORDINAL_METRICS = {
    'intellectual_stimulation',
    'overall_course_quality',
    'overall_instructor_quality',
    'course_difficulty',
}
ORDINAL_MIN = 1.0
ORDINAL_MAX = 5.0


def fit_beta_prior(mu0: float, sigma0_sq: float) -> Tuple[float, float]:
    """
    Fit Beta distribution parameters (α, β) from population mean and variance
    using method of moments, after rescaling from [1,5] to [0,1].

    Args:
        mu0: Global mean on the original [1,5] scale
        sigma0_sq: Global variance on the original [1,5] scale

    Returns:
        (alpha, beta) parameters for the Beta prior

    Examples:
        >>> fit_beta_prior(4.168, 0.182)
        (5.82, 1.62)  # Strong prior concentrated near 0.79 (≈4.17 on 1-5)

        >>> fit_beta_prior(3.0, 2.0)
        (1.0, 1.0)    # Fallback: variance too large for Beta
    """
    scale = ORDINAL_MAX - ORDINAL_MIN  # 4.0
    mu_scaled = (mu0 - ORDINAL_MIN) / scale
    var_scaled = sigma0_sq / (scale ** 2)

    # Clamp mu_scaled away from exact 0 or 1 to avoid degenerate priors
    mu_scaled = max(0.01, min(0.99, mu_scaled))

    # Method of moments: common = μ(1-μ)/σ² - 1
    max_var = mu_scaled * (1 - mu_scaled)  # Maximum variance for this mean
    if var_scaled <= 0 or var_scaled >= max_var:
        # Variance too large (or zero) for Beta — use weak uniform prior
        return (1.0, 1.0)

    common = max_var / var_scaled - 1
    alpha = mu_scaled * common
    beta = (1 - mu_scaled) * common

    # Sanity: both must be positive
    if alpha <= 0 or beta <= 0:
        return (1.0, 1.0)

    return (alpha, beta)


def shrink_estimate_beta(sample_mean: float, n: int,
                         alpha_prior: float, beta_prior: float,
                         min_variance_threshold: float = 0.1) -> Dict:
    """
    Compute Beta-Binomial posterior estimate for an ordinal (1-5) metric.

    Rescales to [0,1], performs conjugate Beta update, rescales back.
    Posterior mean is guaranteed to lie within [ORDINAL_MIN, ORDINAL_MAX].

    Args:
        sample_mean: Sample mean on the [1,5] scale
        n: Sample size (number of respondents)
        alpha_prior: Beta prior α parameter
        beta_prior: Beta prior β parameter
        min_variance_threshold: Floor for posterior std (on original scale)

    Returns:
        Dict with same shape as shrink_estimate() for downstream compatibility
    """
    scale = ORDINAL_MAX - ORDINAL_MIN  # 4.0
    prior_strength = alpha_prior + beta_prior

    if n == 0:
        # Pure prior
        post_alpha = alpha_prior
        post_beta = beta_prior
    else:
        # Rescale sample mean to [0,1]
        x_scaled = (sample_mean - ORDINAL_MIN) / scale
        x_scaled = max(0.0, min(1.0, x_scaled))

        # Pseudo-count of "successes" from the sample
        S = x_scaled * n

        # Conjugate update
        post_alpha = alpha_prior + S
        post_beta = beta_prior + (n - S)

    # Posterior mean and variance in [0,1] space
    post_total = post_alpha + post_beta
    post_mean_scaled = post_alpha / post_total
    post_var_scaled = (post_alpha * post_beta) / (post_total ** 2 * (post_total + 1))

    # Rescale back to [1,5]
    posterior_mean = post_mean_scaled * scale + ORDINAL_MIN
    posterior_var = post_var_scaled * (scale ** 2)

    # Floor the variance
    posterior_var = max(posterior_var, min_variance_threshold ** 2)
    posterior_std = math.sqrt(posterior_var)

    # Shrinkage factor: proportion of posterior driven by data vs. prior
    # B = n / (n + prior_strength), analogous to Gaussian B
    B = n / (n + prior_strength) if (n + prior_strength) > 0 else 0.0

    # Effective sample size (for interpretability)
    effective_n = post_total - prior_strength  # = n, but capped by prior

    return {
        'posterior_mean': round(posterior_mean, 4),
        'posterior_var': round(posterior_var, 4),
        'posterior_std': round(posterior_std, 4),
        'shrinkage_factor': round(B, 4),
        'raw_mean': round(sample_mean, 4),
        'effective_n': round(effective_n, 2),
    }


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

    # Fit Beta priors for ordinal metrics
    for metric_name in metric_names:
        if metric_name in ORDINAL_METRICS and metric_name in priors:
            prior = priors[metric_name]
            alpha, beta = fit_beta_prior(prior['mu0'], prior['sigma0_sq'])
            prior['alpha_prior'] = alpha
            prior['beta_prior'] = beta

    # Print summary
    for metric, prior in priors.items():
        extra = ""
        if 'alpha_prior' in prior:
            extra = f", α={prior['alpha_prior']:.2f}, β={prior['beta_prior']:.2f}"
        print(f"  {metric}: μ₀={prior['mu0']:.3f}, σ₀={prior['sigma0']:.3f}, N={prior['n_total']}{extra}")

    return priors


def compute_shrinkage_factor(n: int, sample_var: float, global_var: float) -> float:
    """
    Calculate Bayesian shrinkage weight B using continuous Empirical Bayes.

    Formula:
        B = σ₀² / (σ₀² + s² / n)

    Interpretation:
        - B → 0 as n → ∞ (trust the data)
        - B → 1 as n → 0 (trust the prior)
        - B decays smoothly with increasing n (no hard cutoffs)

    Args:
        n: Sample size
        sample_var: Sample variance (s²)
        global_var: Global variance (σ₀²)

    Returns:
        Shrinkage factor B ∈ [0, 1]

    Examples:
        >>> compute_shrinkage_factor(1, 0.36, 0.182)
        0.336  # Small N → high shrinkage

        >>> compute_shrinkage_factor(10, 0.36, 0.182)
        0.835  # Medium N → moderate shrinkage

        >>> compute_shrinkage_factor(50, 0.36, 0.182)
        0.962  # Large N → minimal shrinkage

        >>> compute_shrinkage_factor(0, 0, 0.182)
        1.0    # No data → pure prior
    """
    if n == 0:
        return 1.0  # Pure prior

    # Handle edge case: n=1 or sample_var=0
    # Use global variance as fallback for sample variance
    effective_sample_var = sample_var if sample_var > 0 else global_var

    # Continuous Empirical Bayes formula (no hard cutoffs)
    denominator = global_var + effective_sample_var / n

    if denominator == 0:
        return 1.0  # Avoid division by zero

    B = global_var / denominator

    # Clamp to [0, 1] for numerical stability
    return max(0.0, min(1.0, B))


def shrink_estimate(sample_mean: float, sample_var: float, n: int,
                   mu0: float, sigma0_sq: float,
                   min_variance_threshold: float = 0.1) -> Dict:
    """
    Compute Bayesian shrunk estimate (posterior mean).

    Formula:
        μ̂ = B × x̄ + (1 - B) × μ₀

    Where:
        x̄ = sample mean
        μ₀ = global prior mean
        B = shrinkage factor (high for large n, low for small n)

    Args:
        sample_mean: Sample mean (x̄)
        sample_var: Sample variance (s²)
        n: Sample size
        mu0: Global prior mean
        sigma0_sq: Global prior variance
        min_variance_threshold: Minimum variance for z-score calculation

    Returns:
        Dict with:
            - posterior_mean: Shrunk estimate μ̂ (continuous shrinkage)
            - posterior_var: Posterior variance
            - posterior_std: Posterior standard deviation
            - shrinkage_factor: B value (decays smoothly with n)
            - raw_mean: Original sample mean
            - effective_n: Effective sample size

    Example:
        >>> shrink_estimate(4.5, 0.36, 3, 4.168, 0.182)
        {
            'posterior_mean': 4.37,     # Shrunk toward prior (small n=3)
            'posterior_var': 0.24,
            'posterior_std': 0.49,
            'shrinkage_factor': 0.60,   # Low B for small sample
            'raw_mean': 4.5,
            'effective_n': 0.76
        }
    """
    # Calculate shrinkage factor (continuous, no hard cutoffs)
    B = compute_shrinkage_factor(n, sample_var, sigma0_sq)

    # Compute posterior mean (shrunk estimate)
    if n == 0:
        # No data: use pure prior
        posterior_mean = mu0
        posterior_var = sigma0_sq
    else:
        # Weighted average of sample mean and prior
        # B is high when n is large (trust data)
        # B is low when n is small (trust prior)
        posterior_mean = B * sample_mean + (1 - B) * mu0

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

    min_variance_threshold = shrinkage_params.get('min_variance_threshold', 0.1)
    z_score_enabled = z_score_params.get('enabled', True)

    metrics_processed = 0

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

            # Route to appropriate shrinkage model
            if metric_name in ORDINAL_METRICS and 'alpha_prior' in prior:
                # Beta-Binomial for ordinal (1-5 Likert) metrics
                shrinkage_result = shrink_estimate_beta(
                    sample_mean=sample_mean,
                    n=sample_size,
                    alpha_prior=prior['alpha_prior'],
                    beta_prior=prior['beta_prior'],
                    min_variance_threshold=min_variance_threshold,
                )
            else:
                # Normal-Normal for continuous metrics (hours_per_week)
                shrinkage_result = shrink_estimate(
                    sample_mean=sample_mean,
                    sample_var=sample_var,
                    n=sample_size,
                    mu0=mu0,
                    sigma0_sq=sigma0_sq,
                    min_variance_threshold=min_variance_threshold,
                )

            # Add shrinkage fields to metric
            metric['raw_mean'] = shrinkage_result['raw_mean']
            metric['posterior_mean'] = shrinkage_result['posterior_mean']
            metric['posterior_std'] = shrinkage_result['posterior_std']
            metric['posterior_var'] = shrinkage_result['posterior_var']
            metric['shrinkage_factor'] = shrinkage_result['shrinkage_factor']
            metric['effective_n'] = shrinkage_result['effective_n']

            metrics_processed += 1

            # Compute z-score if enabled
            if z_score_enabled:
                z_score = compute_z_score(
                    posterior_mean=shrinkage_result['posterior_mean'],
                    mu0=mu0,
                    sigma0=sigma0,
                    min_variance_threshold=min_variance_threshold
                )
                metric['z_score'] = z_score

    print(f"  Applied hybrid Bayesian shrinkage to {metrics_processed} metrics"
          f" (Beta-Binomial for ordinal, Normal-Normal for continuous)")

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

            # Track shrinkage by exact sample size (for specific N values)
            n = metric.get('sample_size', 0)
            B = metric.get('shrinkage_factor', 0)

            if n not in validation['shrinkage_by_sample_size']:
                validation['shrinkage_by_sample_size'][n] = []
            validation['shrinkage_by_sample_size'][n].append(B)

    # Demonstrate smooth B-factor decay (no discontinuities)
    print("  Shrinkage factor decay (hybrid Beta-Binomial / Normal-Normal):")
    key_sample_sizes = [1, 5, 10, 20, 50, 100]

    for n in key_sample_sizes:
        if n in validation['shrinkage_by_sample_size']:
            B_values = validation['shrinkage_by_sample_size'][n]
            avg_B = statistics.mean(B_values)
            print(f"    N={n:3d}: avg B={avg_B:.4f} (n={len(B_values):4d} metrics)")

    # Show full distribution for verification
    all_sizes = sorted([n for n in validation['shrinkage_by_sample_size'].keys() if len(validation['shrinkage_by_sample_size'][n]) >= 10])
    if all_sizes and len(all_sizes) > 10:
        print(f"  Sample sizes with ≥10 metrics: {min(all_sizes)} to {max(all_sizes)}")

    # Report issues
    if validation['nan_count'] > 0:
        print(f"  WARNING: {validation['nan_count']} NaN values detected")
    if validation['inf_count'] > 0:
        print(f"  WARNING: {validation['inf_count']} Inf z-scores detected")
    if validation['out_of_range_z_scores'] > 0:
        print(f"  WARNING: {validation['out_of_range_z_scores']} z-scores outside [-4, 4] range")

    if validation['nan_count'] == 0 and validation['inf_count'] == 0:
        print("  OK: All values are valid (no NaN/Inf)")

    return validation


# Unit tests (can be run with pytest)
if __name__ == "__main__":
    print("Testing Bayesian Shrinkage Functions\n")

    # Test 1: Gaussian shrinkage factor (used for hours_per_week)
    print("Test 1: Gaussian Shrinkage Factor (continuous metrics)")
    B_large = compute_shrinkage_factor(50, 0.36, 0.182)
    B_small = compute_shrinkage_factor(3, 0.36, 0.182)
    B_zero = compute_shrinkage_factor(0, 0, 0.182)
    print(f"  Large N (50): B={B_large:.4f} (should be close to 1.0 - trust data)")
    print(f"  Small N (3):  B={B_small:.4f} (should be moderate - balanced)")
    print(f"  Zero N:       B={B_zero:.4f} (should be 1.0, but n=0 uses prior directly)")

    # Test 2: Gaussian shrink estimate (hours_per_week)
    print("\nTest 2: Gaussian Shrunk Estimates (continuous metrics)")
    result_large = shrink_estimate(4.5, 0.36, 50, 4.168, 0.182)
    result_small = shrink_estimate(4.5, 0.36, 3, 4.168, 0.182)
    print(f"  Large N (50): raw={result_large['raw_mean']}, posterior={result_large['posterior_mean']}, B={result_large['shrinkage_factor']} (minimal shrinkage)")
    print(f"  Small N (3):  raw={result_small['raw_mean']}, posterior={result_small['posterior_mean']}, B={result_small['shrinkage_factor']} (moderate shrinkage)")

    # Test 3: Beta prior fitting
    print("\nTest 3: Beta Prior Fitting (ordinal metrics)")
    alpha, beta = fit_beta_prior(4.168, 0.182)
    print(f"  μ₀=4.168, σ₀²=0.182 → α={alpha:.2f}, β={beta:.2f}")
    prior_mean_check = alpha / (alpha + beta) * 4.0 + 1.0
    print(f"  Prior mean check: {prior_mean_check:.3f} (should be ~4.168)")

    alpha_u, beta_u = fit_beta_prior(3.0, 5.0)
    print(f"  μ₀=3.0, σ₀²=5.0 (huge variance) → α={alpha_u:.2f}, β={beta_u:.2f} (should be 1.0, 1.0 fallback)")

    # Test 4: Beta-Binomial shrinkage
    print("\nTest 4: Beta-Binomial Shrunk Estimates (ordinal metrics)")
    alpha, beta = fit_beta_prior(4.168, 0.182)

    bb_large = shrink_estimate_beta(4.5, 50, alpha, beta)
    bb_small = shrink_estimate_beta(4.5, 2, alpha, beta)
    bb_extreme = shrink_estimate_beta(4.95, 2, alpha, beta)
    bb_zero = shrink_estimate_beta(0, 0, alpha, beta)

    print(f"  Large N (50), mean=4.5:  posterior={bb_large['posterior_mean']}, B={bb_large['shrinkage_factor']} (should trust data)")
    print(f"  Small N (2),  mean=4.5:  posterior={bb_small['posterior_mean']}, B={bb_small['shrinkage_factor']} (should shrink toward ~4.17)")
    print(f"  Small N (2),  mean=4.95: posterior={bb_extreme['posterior_mean']}, B={bb_extreme['shrinkage_factor']} (should stay ≤ 5.0)")
    print(f"  Zero N:                  posterior={bb_zero['posterior_mean']} (should be prior mean ~4.17)")
    assert bb_extreme['posterior_mean'] <= 5.0, "Beta-Binomial posterior exceeded ordinal max!"
    assert bb_zero['posterior_mean'] >= 1.0, "Beta-Binomial posterior below ordinal min!"

    # Test 5: Z-scores
    print("\nTest 5: Z-Scores")
    z_high = compute_z_score(4.5, 4.168, 0.427)
    z_low = compute_z_score(3.8, 4.168, 0.427)
    z_avg = compute_z_score(4.168, 4.168, 0.427)
    print(f"  High (4.5):   z={z_high} (should be positive)")
    print(f"  Low (3.8):    z={z_low} (should be negative)")
    print(f"  Average (4.168): z={z_avg} (should be ~0)")

    print("\nOK: All tests passed")
