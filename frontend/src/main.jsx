import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import FriendFunClass from './pages/FriendFunClass.jsx'
import './app.css'

const path = window.location.pathname;
const Root = path === '/friend-fun-class' ? FriendFunClass : App;

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>,
)
