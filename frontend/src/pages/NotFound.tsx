import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, FileQuestion } from 'lucide-react';
import { Button } from '@/components/ui/Button';

export function NotFound() {
  return (
    <motion.div
      className="flex flex-col items-center justify-center min-h-[60vh] text-center"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4 }}
    >
      <div className="h-24 w-24 rounded-3xl bg-slate-800/50 flex items-center justify-center mb-6">
        <FileQuestion className="h-12 w-12 text-slate-600" />
      </div>
      <h1 className="text-4xl font-bold text-slate-100 mb-2">404</h1>
      <p className="text-lg text-slate-400 mb-1">Page Not Found</p>
      <p className="text-sm text-slate-500 max-w-md mb-8">
        The page you're looking for doesn't exist or has been moved.
      </p>
      <Link to="/">
        <Button variant="outline">
          <ArrowLeft className="h-4 w-4" />
          Back to Dashboard
        </Button>
      </Link>
    </motion.div>
  );
}
