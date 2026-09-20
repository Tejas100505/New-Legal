/**
 * FileIcon molecule — file type indicator with color coding.
 */

import { cn } from '@/lib/utils';
import { FileText, FileSpreadsheet, Presentation, Mail, Image, File } from 'lucide-react';
import type { DocumentType } from '@/types';

interface FileIconProps {
  type: DocumentType;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const typeConfig: Record<DocumentType, { icon: React.ElementType; bg: string; color: string }> = {
  pdf:  { icon: FileText,         bg: 'bg-red-500/10',    color: 'text-red-400' },
  docx: { icon: FileText,         bg: 'bg-blue-500/10',   color: 'text-blue-400' },
  txt:  { icon: File,             bg: 'bg-slate-500/10',  color: 'text-slate-400' },
  eml:  { icon: Mail,             bg: 'bg-amber-500/10',  color: 'text-amber-400' },
  xlsx: { icon: FileSpreadsheet,  bg: 'bg-emerald-500/10',color: 'text-emerald-400' },
  pptx: { icon: Presentation,     bg: 'bg-orange-500/10', color: 'text-orange-400' },
  jpg:  { icon: Image,            bg: 'bg-violet-500/10', color: 'text-violet-400' },
  png:  { icon: Image,            bg: 'bg-violet-500/10', color: 'text-violet-400' },
};

const sizeStyles = {
  sm: { container: 'h-8 w-8', icon: 'h-4 w-4' },
  md: { container: 'h-10 w-10', icon: 'h-5 w-5' },
  lg: { container: 'h-12 w-12', icon: 'h-6 w-6' },
};

export function FileIcon({ type, size = 'md', className }: FileIconProps) {
  const config = typeConfig[type] || typeConfig.txt;
  const sizing = sizeStyles[size];
  const Icon = config.icon;

  return (
    <div
      className={cn(
        'rounded-lg flex items-center justify-center shrink-0',
        config.bg,
        sizing.container,
        className
      )}
    >
      <Icon className={cn(config.color, sizing.icon)} />
    </div>
  );
}
