import { LayoutDashboard, BrainCircuit, Map, Image as ImageIcon } from "lucide-react";

interface PreviewCardProps {
  title: string;
  description: string;
  icon: React.ElementType;
  imageSrc?: string;
}

function PreviewCard({ title, description, icon: Icon, imageSrc }: PreviewCardProps) {
  return (
    <div className="flex h-full flex-col gap-4 rounded-2xl border border-slate-800 bg-slate-900/50 p-4 shadow-xl">
      <div className="flex items-center gap-3 px-2 pt-2">
        <Icon className="h-5 w-5 text-indigo-400" />
        <div>
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-200">{title}</h3>
          <p className="text-xs text-slate-400">{description}</p>
        </div>
      </div>
      <div className="relative flex-1 overflow-hidden rounded-xl border border-slate-800 bg-slate-950 min-h-[200px] sm:min-h-[300px] flex items-center justify-center">
        {imageSrc ? (
          <img src={imageSrc} alt={`${title} Preview`} className="h-full w-full object-cover" />
        ) : (
          <div className="flex flex-col items-center gap-3 text-slate-600">
            <ImageIcon className="h-8 w-8 opacity-50" />
            <span className="text-sm font-medium uppercase tracking-wider">Screenshot Coming Soon</span>
          </div>
        )}
      </div>
    </div>
  );
}

export function PreviewSection() {
  return (
    <section className="overflow-hidden px-6 py-24 lg:px-8">
      <div className="mx-auto max-w-6xl">
        <div className="mb-16 text-center">
          <h2 className="text-3xl font-bold tracking-tight text-slate-50 sm:text-4xl">
            Example Output Preview
          </h2>
          <p className="mt-4 text-lg text-slate-400">See how RepoGuideAI breaks down complex repositories.</p>
        </div>
        <div className="flex flex-col gap-12">
          <PreviewCard 
            title="Repository Overview" 
            description="Understand the big picture and codebase architecture."
            icon={LayoutDashboard}
            /* imageSrc="/design_reference/full-analysis.png" */
          />
          <div className="grid grid-cols-1 gap-8 md:grid-cols-2">
            <PreviewCard 
              title="Issue Analysis" 
              description="Translate complex issues into beginner-friendly explanations."
              icon={BrainCircuit}
              /* imageSrc="/design_reference/issue-analysis.png" */
            />
            <PreviewCard 
              title="Exploration Hints" 
              description="Targeted starting points to investigate the codebase."
              icon={Map}
              /* imageSrc="/design_reference/issue-discovery.png" */
            />
          </div>
        </div>
      </div>
    </section>
  );
}