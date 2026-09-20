/**
 * UserAvatar molecule — user profile avatar with status.
 */

import { cn } from '@/lib/utils';
import { User } from 'lucide-react';

interface UserAvatarProps {
  name: string;
  avatar?: string;
  size?: 'sm' | 'md' | 'lg';
  showStatus?: boolean;
  status?: 'online' | 'away' | 'offline';
  className?: string;
}

const sizeStyles = {
  sm: 'h-7 w-7 text-xs',
  md: 'h-9 w-9 text-sm',
  lg: 'h-12 w-12 text-base',
};

const statusSizeStyles = {
  sm: 'h-2 w-2 -bottom-0 -right-0',
  md: 'h-2.5 w-2.5 -bottom-0.5 -right-0.5',
  lg: 'h-3 w-3 -bottom-0.5 -right-0.5',
};

const statusColorStyles = {
  online: 'bg-emerald-400',
  away: 'bg-amber-400',
  offline: 'bg-slate-500',
};

function getInitials(name: string): string {
  return name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

export function UserAvatar({ name, avatar, size = 'md', showStatus, status = 'online', className }: UserAvatarProps) {
  return (
    <div className={cn('relative inline-flex', className)}>
      {avatar ? (
        <img
          src={avatar}
          alt={name}
          className={cn(
            'rounded-lg object-cover',
            sizeStyles[size]
          )}
        />
      ) : (
        <div
          className={cn(
            'rounded-lg bg-gradient-to-br from-indigo-500 to-violet-500',
            'flex items-center justify-center font-semibold text-white',
            sizeStyles[size]
          )}
          aria-label={name}
        >
          {name ? getInitials(name) : <User className="h-4 w-4" />}
        </div>
      )}
      {showStatus && (
        <span
          className={cn(
            'absolute rounded-full ring-2 ring-slate-950 dark:ring-slate-950',
            statusSizeStyles[size],
            statusColorStyles[status]
          )}
        />
      )}
    </div>
  );
}
