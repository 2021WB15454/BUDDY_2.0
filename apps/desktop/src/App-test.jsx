import React from 'react';
import './styles/App.css';

function App() {
  return (
    <div className="app">
      <h1 style={{color: 'white', textAlign: 'center', marginTop: '50px'}}>
        BUDDY App Test - React is Working!
      </h1>
      <div style={{color: 'white', textAlign: 'center', marginTop: '20px'}}>
        <p>If you can see this, React is rendering correctly.</p>
        <button onClick={() => alert('Button clicked!')}>Test Button</button>
      </div>
    </div>
  );
}

export default App;
