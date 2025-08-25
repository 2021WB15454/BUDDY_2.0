# BUDDY Desktop Application

A cross-platform desktop application built with Electron and React that provides a rich interface for interacting with your BUDDY AI assistant.

## Features

- **Multi-Modal Interface**: Switch between chat and voice interaction modes
- **Skills Management**: Install, configure, and manage BUDDY's capabilities
- **Real-time Status**: Monitor system status, connection health, and active processes
- **Voice Integration**: Full voice recognition and text-to-speech capabilities
- **Settings Management**: Comprehensive configuration options
- **Cross-Platform**: Works on Windows, macOS, and Linux

## Architecture

```
apps/desktop/
├── src/
│   ├── components/           # React UI components
│   │   ├── Sidebar.jsx      # Navigation sidebar
│   │   ├── ChatInterface.jsx # Text chat interface
│   │   ├── VoiceInterface.jsx # Voice interaction UI
│   │   ├── SkillsPanel.jsx  # Skills management panel
│   │   ├── SettingsPanel.jsx # Configuration settings
│   │   └── StatusBar.jsx    # System status display
│   ├── hooks/               # Custom React hooks
│   │   ├── useBuddy.js     # BUDDY backend integration
│   │   └── useVoice.js     # Voice processing hooks
│   ├── styles/             # CSS stylesheets
│   │   └── App.css         # Main application styles
│   ├── App.jsx             # Main application component
│   └── index.js            # React entry point
├── public/                 # Static assets
├── main.js                 # Electron main process
├── preload.js             # Electron preload script
└── package.json           # Dependencies and scripts
```

## Components

### Core Components

1. **App.jsx** - Main application orchestrator
   - Manages global state and routing
   - Coordinates between components
   - Handles system monitoring and error management

2. **Sidebar.jsx** - Navigation and status
   - View switching (Chat, Voice, Skills, Settings)
   - Connection status indicator
   - System statistics display

3. **ChatInterface.jsx** - Text-based interaction
   - Message history display
   - Text input and formatting
   - Voice integration toggle

4. **VoiceInterface.jsx** - Voice interaction
   - Microphone controls
   - Real-time voice visualization
   - Speech recognition feedback

5. **SkillsPanel.jsx** - Skills management
   - Browse available skills
   - Install/uninstall capabilities
   - Configure skill settings

6. **SettingsPanel.jsx** - Configuration
   - General preferences
   - Voice settings
   - Privacy controls
   - Advanced options

7. **StatusBar.jsx** - System monitoring
   - Connection status
   - Voice state
   - System resource usage
   - Error notifications

### Hooks

1. **useBuddy.js** - Backend communication
   - WebSocket connection management
   - Message sending/receiving
   - Status monitoring

2. **useVoice.js** - Voice processing
   - Microphone access
   - Speech recognition
   - Voice activity detection

## Development

### Prerequisites

- Node.js 18+ and npm/yarn
- Python 3.9+ (for BUDDY backend)
- Git

### Setup

1. **Install dependencies:**
   ```bash
   cd apps/desktop
   npm install
   ```

2. **Start BUDDY backend:**
   ```bash
   cd packages/core
   python -m buddy.main
   ```

3. **Run development server:**
   ```bash
   cd apps/desktop
   npm run dev
   ```

### Building

1. **Build for production:**
   ```bash
   npm run build
   ```

2. **Package as executable:**
   ```bash
   npm run package
   ```

3. **Create installers:**
   ```bash
   npm run dist
   ```

## Configuration

The app connects to the BUDDY backend running on `http://localhost:8000` by default. This can be configured in the settings panel or via environment variables:

```bash
BUDDY_BACKEND_URL=http://localhost:8000
BUDDY_WS_URL=ws://localhost:8000/ws
```

## IPC Communication

The desktop app communicates with the Python backend through Electron's IPC system:

### Available IPC Channels

- `buddy-send-message` - Send message to BUDDY
- `buddy-get-status` - Get system status
- `buddy-get-skills` - Get installed skills
- `buddy-toggle-skill` - Enable/disable skill
- `buddy-get-settings` - Get configuration
- `buddy-save-settings` - Save configuration
- `get-system-stats` - Get system metrics

### WebSocket Events

- `message` - New message received
- `status_update` - System status changed
- `skill_update` - Skill status changed
- `error` - Error occurred

## Styling

The application uses a modern, responsive design with:

- CSS custom properties for theming
- Dark/light mode support
- Mobile-responsive layouts
- Smooth animations and transitions
- Material Design inspired components

### Theme Variables

```css
:root {
  --bg-primary: #ffffff;
  --bg-secondary: #f8f9fa;
  --text-primary: #212529;
  --border-color: #dee2e6;
  --accent-color: #007bff;
  /* ... more variables */
}
```

## Error Handling

The application includes comprehensive error handling:

- Connection failure recovery
- Voice permission handling
- Graceful degradation when features unavailable
- User-friendly error messages
- Automatic retry mechanisms

## Security

- Sandboxed renderer processes
- Context isolation enabled
- No Node.js integration in renderer
- Secure IPC communication
- Local data encryption (when enabled)

## Performance

Optimizations include:

- Lazy loading of heavy components
- Efficient state management
- Minimal re-renders
- Audio processing in web workers
- Connection pooling

## Accessibility

Features for accessibility:

- Keyboard navigation support
- Screen reader compatibility
- High contrast mode
- Focus indicators
- ARIA labels and roles

## Troubleshooting

### Common Issues

1. **Voice not working**
   - Check microphone permissions
   - Verify audio device availability
   - Test in browser DevTools

2. **Connection issues**
   - Ensure BUDDY backend is running
   - Check network configuration
   - Verify firewall settings

3. **Performance issues**
   - Close unnecessary applications
   - Check system resources
   - Clear application cache

### Debug Mode

Enable debug mode in settings for:
- Detailed logging
- Performance metrics
- Network request inspection
- State debugging tools

## License

This project is part of the BUDDY AI Assistant system and follows the same licensing terms.
