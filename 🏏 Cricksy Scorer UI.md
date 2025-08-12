# 🏏 Cricksy Scorer UI

Professional cricket scoring application frontend built with Vue.js 3, designed specifically for school cricket matches.

## Features

- **Real-time Scoring**: Score deliveries instantly with intuitive controls
- **Detailed Statistics**: Comprehensive batting and bowling scorecards
- **School-Focused**: Designed for 25-over school cricket matches
- **Mobile Friendly**: Works perfectly on tablets and mobile devices
- **Professional Design**: Clean, modern interface with accessibility features

## Technology Stack

- **Vue.js 3** with Composition API
- **TypeScript** for type safety
- **Vite** for fast development and optimized builds
- **Vue Router** for client-side routing
- **Pinia** for state management
- **Pico CSS** for base styling
- **ESLint & Prettier** for code quality

## Project Structure

```
cricksy-scorer-ui/
├── public/                 # Static assets
├── src/
│   ├── components/         # Vue components
│   │   ├── common/        # Shared components
│   │   ├── game/          # Game-related components
│   │   └── scoring/       # Scoring components
│   ├── views/             # Page components
│   ├── stores/            # Pinia stores
│   ├── types/             # TypeScript definitions
│   ├── utils/             # Utility functions
│   ├── assets/            # Styles and assets
│   ├── router/            # Vue Router configuration
│   ├── App.vue            # Root component
│   └── main.ts            # Application entry point
├── package.json
├── vite.config.ts         # Vite configuration
└── tsconfig.json          # TypeScript configuration
```

## Development Setup

### Prerequisites

- Node.js 18+ 
- npm or yarn
- Backend API running on http://localhost:8000

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd cricksy-scorer-ui
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

4. Open your browser and navigate to `http://localhost:3000`

### Available Scripts

- `npm run dev` - Start development server with hot reload
- `npm run build` - Build for production
- `npm run preview` - Preview production build locally
- `npm run type-check` - Run TypeScript type checking
- `npm run lint` - Run ESLint
- `npm run format` - Format code with Prettier

## API Integration

The frontend is configured to proxy API requests to the FastAPI backend:

- Development: `http://localhost:8000`
- API calls are made to `/api/*` and automatically proxied

## Configuration

### Environment Variables

Create a `.env` file for environment-specific configuration:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_TITLE=Cricksy Scorer
```

### Vite Configuration

The `vite.config.ts` file includes:

- Path aliases (`@/` for `src/`)
- API proxy configuration
- Build optimizations
- Development server settings

## Code Style

This project uses:

- **ESLint** for code linting
- **Prettier** for code formatting
- **TypeScript** strict mode
- **Vue 3 Composition API** patterns

## Browser Support

- Chrome/Chromium 88+
- Firefox 85+
- Safari 14+
- Edge 88+

## Contributing

1. Follow the existing code style
2. Write TypeScript with strict typing
3. Use Vue 3 Composition API
4. Add proper error handling
5. Include responsive design
6. Test on multiple devices

## Deployment

### Production Build

```bash
npm run build
```

The built files will be in the `dist/` directory.

### Docker Deployment

A Dockerfile will be provided in future versions for containerized deployment.

## License

This project is licensed under the MIT License.

## Support

For support and questions, please contact the development team.

---

Built with ❤️ for school cricket programs

