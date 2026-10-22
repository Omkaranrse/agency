/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  compress: true,
  experimental: {
    optimizePackageImports: [
      'lucide-react',
      '@react-three/drei',
      'three',
      'framer-motion',
    ],
  },
};

export default nextConfig;
