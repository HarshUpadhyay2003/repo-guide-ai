import { HeroSection } from "../components/landing/HeroSection";
import { CommunityBanner } from "../components/landing/CommunityBanner";
import { ProblemSection } from "../components/landing/ProblemSection";
import { FeaturesSection } from "../components/landing/FeaturesSection";
import { HowItWorksSection } from "../components/landing/HowItWorksSection";
import { PreviewSection } from "../components/landing/PreviewSection";
import { ValidatedSection } from "../components/landing/ValidatedSection";
import { FinalCtaSection } from "../components/landing/FinalCtaSection";

export default function LandingPage() {
  return (
    <div className="flex flex-col font-sans selection:bg-indigo-500/30">
      <HeroSection />
      <CommunityBanner />
      <ProblemSection />
      <FeaturesSection />
      <HowItWorksSection />
      <PreviewSection />
      <ValidatedSection />
      <FinalCtaSection />
    </div>
  );
}