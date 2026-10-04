/**
 * Breadcrumbs molecule — auto-generated from React Router location.
 */

import { Link, useLocation } from 'react-router-dom';
import { ChevronRight, Home } from 'lucide-react';
import { ROUTE_META } from '@/lib/constants';
import { cn } from '@/lib/utils';

export function Breadcrumbs({ className }: { className?: string }) {
  const location = useLocation();
  const segments = location.pathname.split('/').filter(Boolean);

  const crumbs = segments.map((segment, index) => {
    let path = '/' + segments.slice(0, index + 1).join('/');
    const meta = ROUTE_META[path];
    const isUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(segment);

    let label = meta?.title;
    if (!label) {
      if (isUuid) {
        if (segments[index - 1] === 'cases') {
          label = 'Workspace';
          path = `${path}/overview`;
        } else if (segments[index - 1] === 'documents') {
          label = 'Document';
        } else {
          label = segment.slice(0, 8);
        }
      } else {
        label = segment.charAt(0).toUpperCase() + segment.slice(1).replace(/-/g, ' ');
      }
    }

    const isLast = index === segments.length - 1;

    return { path, label, isLast };
  });

  return (
    <nav
      aria-label="Breadcrumb"
      className={cn('flex items-center gap-1.5 text-sm', className)}
    >
      <Link
        to="/"
        className="flex items-center gap-1 text-slate-500 hover:text-slate-300 transition-colors"
        aria-label="Home"
      >
        <Home className="h-3.5 w-3.5" />
      </Link>

      {crumbs.map((crumb) => (
        <div key={crumb.path} className="flex items-center gap-1.5">
          <ChevronRight className="h-3.5 w-3.5 text-slate-700" />
          {crumb.isLast ? (
            <span className="text-slate-300 font-medium" aria-current="page">
              {crumb.label}
            </span>
          ) : (
            <Link
              to={crumb.path}
              className="text-slate-500 hover:text-slate-300 transition-colors"
            >
              {crumb.label}
            </Link>
          )}
        </div>
      ))}
    </nav>
  );
}
