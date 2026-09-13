# Paperwork Agent UI

A modern Next.js UI for the Paperwork Agent concept: a personal administrative workspace that turns a user's goal into a verified, reviewable paperwork package.

## Stack

- Next.js 16.3.3
- React 19.3
- TypeScript
- Tailwind CSS 4.3
- App Router
- Cache Components
- Turbopack

## Included screens

- Dashboard
- New request
- Document vault
- Applications
- Passport application detail
- Settings

## Run locally

```bash
npm install
npm run dev
```

Open `http://localhost:3000`.

## Build

```bash
npm run build
npm start
```

## Structure

```text
app/
components/
  ui/
lib/
public/
```

Most components are Server Components. Only navigation state, request composition, and local file selection use client components.
