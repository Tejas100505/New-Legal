import { useMemo } from 'react';
import { useDocumentViewerStore } from '../store/documentViewerStore';
import { Search, ChevronRight, FileText } from 'lucide-react';

interface DocumentSearchProps {
  onJumpToPage: (page: number) => void;
}

export function DocumentSearch({ onJumpToPage }: DocumentSearchProps) {
  const searchQuery = useDocumentViewerStore((s) => s.searchQuery);
  const setSearchQuery = useDocumentViewerStore((s) => s.setSearchQuery);

  const mockText = `MUTUAL NON-DISCLOSURE AGREEMENT
This Mutual Non-Disclosure Agreement (the "Agreement") is entered into as of May 14, 2023 (the "Effective Date") by and between Meridian Corporation, a California Corporation with offices at 100 Innovation Way, San Jose, California (the "Disclosing Party") and John Miller, an individual residing in Austin, Texas (the "Receiving Party").

WHEREAS, the Disclosing Party has developed certain proprietary manufacturing processes and chemical mechanical planarization technologies (collectively, "Proprietary Information") related to high-performance semiconductor components;

NOW, THEREFORE, the parties agree that the Receiving Party shall keep strictly confidential all Proprietary Information and shall not disclose or exploit such information for a period of five (5) years from disclosure.

In the event of a breach or threatened breach, the Disclosing Party shall be entitled to seek injunctive relief without the necessity of posting a bond, as verified in Smith v. Johnson (2019) 14 Cal.4th 23. This Agreement shall be governed by and construed in accordance with the laws of the State of California.`;

  // Parse lines and simulate occurrences
  const results = useMemo(() => {
    if (!searchQuery || searchQuery.length < 2) return [];
    const query = searchQuery.toLowerCase();
    const matches: Array<{ page: number; text: string; snippet: string }> = [];

    // Simulate search matches across mock pages
    const paragraphs = mockText.split('\n\n');
    paragraphs.forEach((p, idx) => {
      if (p.toLowerCase().includes(query)) {
        const sentence = p.split('.').find((s) => s.toLowerCase().includes(query)) || p;
        const pageNum = (idx % 3) + 1; // distribute matches across simulated pages 1-3
        matches.push({
          page: pageNum,
          text: query,
          snippet: sentence.trim() + '.',
        });
      }
    });

    return matches;
  }, [searchQuery]);

  return (
    <div className="flex flex-col gap-4 text-left">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search text in document..."
          className="w-full pl-10 pr-4 py-2 rounded-lg bg-slate-800/60 border border-slate-700/50 text-sm text-slate-200 placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 transition-all"
        />
      </div>

      <div className="flex flex-col gap-2">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
          Search Results ({results.length})
        </span>

        {results.length > 0 ? (
          <div className="flex flex-col gap-2 max-h-[300px] overflow-y-auto pr-1">
            {results.map((res, i) => (
              <button
                key={i}
                onClick={() => onJumpToPage(res.page)}
                className="w-full p-2.5 rounded-lg bg-slate-950/40 border border-slate-850 hover:border-slate-700 hover:bg-slate-900/30 transition-all text-left flex items-start gap-2.5 group"
              >
                <FileText className="h-4 w-4 text-indigo-400 shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-[10px] font-bold text-indigo-300">PAGE {res.page}</span>
                    <ChevronRight className="h-3 w-3 text-slate-600 group-hover:text-slate-400 transition-colors" />
                  </div>
                  <p className="text-xs text-slate-300 leading-normal" dangerouslySetInnerHTML={{
                    __html: res.snippet.replace(new RegExp(res.text, 'gi'), (m) => `<mark class="bg-indigo-500/30 text-indigo-200 px-0.5 rounded font-semibold">${m}</mark>`)
                  }} />
                </div>
              </button>
            ))}
          </div>
        ) : (
          searchQuery && (
            <div className="text-center text-xs text-slate-600 py-6 bg-slate-950/10 border border-dashed border-slate-850 rounded-lg">
              No occurrences found in text.
            </div>
          )
        )}
      </div>
    </div>
  );
}
