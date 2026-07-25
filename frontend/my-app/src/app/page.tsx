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
    <div className="flex flex-col font-sans selection:bg-[#8B5CF6]/30">
      <HeroSection />
      <CommunityBanner />
      <ProblemSection />
      <FeaturesSection />
      <HowItWorksSection />
      {/* TODO(v1.1): Re-enable Example Output Preview after creating production animated GIF demonstrations */}
      {/* <PreviewSection /> */}
      <ValidatedSection />
      <FinalCtaSection />
    </div>
  );
}