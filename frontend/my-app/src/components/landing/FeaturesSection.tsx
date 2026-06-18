import { BookOpen, FolderTree, BrainCircuit, Map } from "lucide-react";

const features = [
  {
    title: "Repository Summary",
    description: "Understand repository purpose, difficulty, learning time, and target users.",
    icon: BookOpen,
    color: "text-indigo-400"
  },
  {
    title: "Repository Map",
    description: "Explore important frontend, backend, test, and configuration areas.",
    icon: FolderTree,
    color: "text-blue-400"
  },
  {
    title: "Issue Analysis",
    description: "Translate complex GitHub issues into beginner-friendly explanations.",
    icon: BrainCircuit,
    color: "text-emerald-400"
  },
  {
    title: "Exploration Hints",
    description: "Discover likely directories and files before reading thousands of lines of code.",
    icon: Map,
    color: "text-amber-400"
  }
];

export function FeaturesSection() {
  return (
    <section className="px-6 py-24 lg:px-8">
      <div className="mx-auto max-w-5xl">
        <div className="mb-16 text-center">
          <h2 className="text-3xl font-bold tracking-tight text-slate-50 sm:text-4xl">
            Your Personalized Contribution Guide
          </h2>
        </div>
        <div className="grid grid-cols-1 gap-8 md:grid-cols-2">
          {features.map((feature, idx) => (
            <div key={idx} className="flex flex-col gap-4 rounded-2xl border border-slate-800 bg-slate-900/40 p-6 shadow-sm transition-colors hover:bg-slate-800/40 sm:p-8">
              <div className="flex items-center gap-3">
                <feature.icon className={`h-6 w-6 ${feature.color}`} />
                <h3 className="text-xl font-bold text-slate-100">{feature.title}</h3>
              </div>
              <p className="text-base leading-relaxed text-slate-400">
                {feature.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}