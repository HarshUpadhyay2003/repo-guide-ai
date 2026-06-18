const steps = [
  { title: "Paste Repository URL", description: "Start by providing the GitHub URL of any supported open-source project." },
  { title: "AI Analyzes Repository", description: "We extract the structure, summarize the documentation, and evaluate issues." },
  { title: "Receive Contribution Guide", description: "Get a clear roadmap showing you exactly where and how to start contributing." }
];

export function HowItWorksSection() {
  return (
    <section className="border-y border-slate-800/60 bg-slate-900/20 py-24">
      <div className="mx-auto max-w-6xl px-6 lg:px-8">
        <div className="mb-16 text-center">
          <h2 className="text-3xl font-bold tracking-tight text-slate-50 sm:text-4xl">
            How It Works
          </h2>
        </div>
        <div className="grid grid-cols-1 gap-8 md:grid-cols-3">
          {steps.map((step, idx) => (
            <div key={idx} className="relative flex flex-col gap-6">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-600 text-2xl font-bold text-white shadow-md">
                {idx + 1}
              </div>
              <div>
                <h3 className="mb-2 text-xl font-bold text-slate-100">{step.title}</h3>
                <p className="leading-relaxed text-slate-400">{step.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}