import { useState } from 'react';
import { Badge } from '@/components/atoms/Badge';
import { Users, Building, Calendar, MapPin, Scale, Hash, DollarSign, FileText } from 'lucide-react';

interface EntityPanelProps {
  doc?: any;
}

export function EntityPanel({ doc }: EntityPanelProps) {
  const [activeCategory, setActiveCategory] = useState<string>('all');
  const rawEntities = doc?.doc_metadata?.entities || {};

  // Normalize entity structure: entities is a dict with category keys
  // e.g. { people: [...], organizations: [...], dates: [...], locations: [...], courts: [...], case_numbers: [...], money: [...] }
  const categories: { key: string; label: string; icon: React.ElementType; items: string[] }[] = [
    { key: 'people', label: 'People', icon: Users, items: Array.isArray(rawEntities.people) ? rawEntities.people : [] },
    { key: 'organizations', label: 'Organizations', icon: Building, items: Array.isArray(rawEntities.organizations) ? rawEntities.organizations : [] },
    { key: 'dates', label: 'Dates & Chronology', icon: Calendar, items: Array.isArray(rawEntities.dates) ? rawEntities.dates : [] },
    { key: 'locations', label: 'Locations', icon: MapPin, items: Array.isArray(rawEntities.locations) ? rawEntities.locations : [] },
    { key: 'courts', label: 'Courts & Tribunals', icon: Scale, items: Array.isArray(rawEntities.courts) ? rawEntities.courts : [] },
    { key: 'case_numbers', label: 'Case References', icon: Hash, items: Array.isArray(rawEntities.case_numbers) ? rawEntities.case_numbers : [] },
    { key: 'money', label: 'Financial & Monetary', icon: DollarSign, items: Array.isArray(rawEntities.money) ? rawEntities.money : [] },
  ];

  const totalEntityCount = categories.reduce((sum, cat) => sum + cat.items.length, 0);

  const filteredCategories = activeCategory === 'all'
    ? categories.filter(c => c.items.length > 0)
    : categories.filter(c => c.key === activeCategory && c.items.length > 0);

  if (totalEntityCount === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-center text-slate-500 rounded-xl bg-slate-900/30 border border-slate-800">
        <FileText className="h-8 w-8 text-slate-600 mb-2" />
        <h4 className="text-xs font-semibold text-slate-400">No Entities Extracted</h4>
        <p className="text-[11px] text-slate-500 mt-1 max-w-xs">
          No named entities were detected or indexed for this document during pipeline analysis.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 text-left">
      {/* Category Filter Pills */}
      <div className="flex flex-wrap gap-1 bg-slate-950/40 p-2 rounded-lg border border-slate-850">
        <button
          onClick={() => setActiveCategory('all')}
          className={`px-2.5 py-1 rounded text-[11px] font-semibold transition-all ${
            activeCategory === 'all'
              ? 'bg-indigo-600 text-white'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          All ({totalEntityCount})
        </button>
        {categories.map((cat) => {
          if (cat.items.length === 0) return null;
          const active = activeCategory === cat.key;
          return (
            <button
              key={cat.key}
              onClick={() => setActiveCategory(cat.key)}
              className={`px-2 py-1 rounded text-[11px] font-semibold transition-all flex items-center gap-1 ${
                active
                  ? 'bg-indigo-600 text-white'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <cat.icon className="h-3 w-3" />
              <span>{cat.label} ({cat.items.length})</span>
            </button>
          );
        })}
      </div>

      {/* Render Entities by Category */}
      <div className="space-y-4">
        {filteredCategories.map((cat) => (
          <div key={cat.key} className="space-y-2">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">
              <cat.icon className="h-3.5 w-3.5 text-indigo-400" />
              <span>{cat.label}</span>
              <span className="text-[10px] text-slate-500">({cat.items.length})</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {cat.items.map((item, idx) => (
                <Badge
                  key={`${cat.key}-${idx}`}
                  variant={
                    cat.key === 'people'
                      ? 'info'
                      : cat.key === 'organizations'
                      ? 'purple'
                      : cat.key === 'courts'
                      ? 'warning'
                      : cat.key === 'money'
                      ? 'success'
                      : 'outline'
                  }
                  size="sm"
                  className="font-medium text-xs px-2.5 py-1"
                >
                  {item}
                </Badge>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
