# Discord Game Scheduler - Frontend

React + TypeScript + Vite frontend for the Discord Game Scheduler application.

## Tech Stack

- **React 18** - UI library
- **TypeScript 5** - Type safety
- **Vite** - Build tool and dev server
- **Material-UI 5** - Component library
- **React Router 6** - Client-side routing
- **Axios** - HTTP client

## Getting Started

### Prerequisites

- Node.js 22+ or Bun
- Running API service at http://localhost:8000

### Installation

```bash
# Install dependencies
npm install
# or
bun install
```

### Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Edit `.env`:

```
VITE_API_URL=http://localhost:8000
VITE_DISCORD_CLIENT_ID=your_discord_client_id
```

### Development

```bash
# Start dev server
npm run dev
# or
bun run dev
```

App runs at http://localhost:3000

### Build

```bash
# Type check
npm run type-check

# Build for production
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
src/
├── api/           # API client and request functions
├── components/    # Reusable UI components
├── contexts/      # React contexts (Auth, etc.)
├── hooks/         # Custom React hooks
├── pages/         # Route page components
├── types/         # TypeScript type definitions
├── App.tsx        # Root component with routing
├── index.tsx      # Entry point
└── theme.ts       # Material-UI theme
```

## Features

- Discord OAuth2 authentication
- Protected routes with auth guards
- Automatic token refresh
- Material-UI themed components
- Responsive design
- TypeScript strict mode

## Contributing

Follow the project's TypeScript and React conventions. Run `npm run lint` before committing.
