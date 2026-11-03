import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = { title: 'LearnPilot AI | Your personal learning copilot', description: 'Turn study materials into interactive learning experiences.' };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body>{children}</body></html>; }
