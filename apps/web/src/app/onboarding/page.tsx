'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence, Variants } from 'framer-motion';
import { 
  Code, 
  PenTool, 
  BookOpen, 
  Cloud, 
  Github, 
  HardDrive, 
  ArrowRight, 
  ArrowLeft,
  Check,
  Zap
} from 'lucide-react';
import { useTheme } from '@/components/providers/theme-provider';
import { cn } from '@/lib/utils';

export default function OnboardingPage() {
  const router = useRouter();
  const { theme } = useTheme();
  const isPlana = theme === 'dark';
  
  const [step, setStep] = useState(1);
  const [direction, setDirection] = useState(0);
  const [formData, setFormData] = useState({
    userName: '',
    specialization: '',
    dataSources: [] as string[],
    agentName: '',
    tone: 'Professional',
    directives: ''
  });

  const variants: Variants = {
    enter: (direction: number) => ({
      x: direction > 0 ? 50 : -50,
      opacity: 0,
      filter: 'blur(10px)',
    }),
    center: {
      x: 0,
      opacity: 1,
      filter: 'blur(0px)',
      transition: {
        duration: 0.4,
        ease: "easeOut"
      }
    },
    exit: (direction: number) => ({
      x: direction < 0 ? 50 : -50,
      opacity: 0,
      filter: 'blur(10px)',
      transition: {
        duration: 0.3,
        ease: "easeIn"
      }
    })
  };

  const handleNext = () => {
    if (step < 4) {
      setDirection(1);
      setStep(step + 1);
    } else {
      // Complete onboarding
      router.push('/');
    }
  };

  const handleBack = () => {
    if (step > 1) {
      setDirection(-1);
      setStep(step - 1);
    }
  };

  const toggleDataSource = (source: string) => {
    setFormData(prev => ({
      ...prev,
      dataSources: prev.dataSources.includes(source)
        ? prev.dataSources.filter(d => d !== source)
        : [...prev.dataSources, source]
    }));
  };

  return (
    <div className={cn(
        "flex min-h-screen flex-col items-center justify-center p-4 font-sans transition-colors",
        isPlana 
            ? "bg-[#0d1117] text-slate-200" 
            : "bg-[linear-gradient(135deg,_#fdfeff_0%,_#e3f2fd_100%)] text-slate-700"
    )}>
      {/* Progress Bar */}
      <div className={cn("fixed top-0 left-0 w-full h-1", isPlana ? "bg-slate-900" : "bg-white")}>
        <motion.div 
          className={cn("h-full shadow-[0_0_10px]", isPlana ? "bg-rose-600 shadow-rose-900/50" : "bg-blue-400 shadow-blue-400/50")}
          initial={{ width: "33%" }}
          animate={{ width: step === 4 ? "100%" : `${step * 33.33}%` }}
          transition={{ duration: 0.5 }}
        />
      </div>

      <div className={cn(
          "w-full max-w-2xl backdrop-blur-md border rounded-[2rem] p-8 md:p-12 shadow-2xl relative overflow-hidden transition-all",
          isPlana 
            ? "bg-[#161b22]/80 border-rose-900/30 shadow-none" 
            : "bg-white/40 border-blue-100 shadow-blue-200/20"
      )}>
        
        {/* Header decoration */}
        <div className="absolute top-8 right-10 text-right hidden md:block">
          <span className={cn("block font-mono text-[10px]", isPlana ? "text-rose-400/60" : "text-blue-300")}>
            {step === 1 ? 'LINK_STATUS: READY' : step === 2 ? 'SYNCHRONIZE_STATUS: READY' : step === 3 ? 'ENCRYPTION: AES-256' : 'SYSTEM: ONLINE'}
          </span>
          <span className={cn("block font-mono text-[10px] tracking-tighter", isPlana ? "text-rose-500" : "text-blue-400")}>
             {step === 1 ? 'BITRATE: -- MBPS' : step === 2 ? 'BITRATE: 1024 MBPS' : step === 3 ? 'CALIBRATION_ACTIVE' : 'CONNECTED'}
          </span>
        </div>

        {/* Floating Halo Animation */}
        {step < 4 && (
        <div className="absolute -top-16 left-1/2 -translate-x-1/2">
          <div className={cn(
              "h-32 w-32 animate-[spin_10s_linear_infinite] rounded-full border-2 border-dashed opacity-30",
              isPlana ? "border-rose-700" : "border-blue-300"
          )}></div>
          <div className={cn(
              "absolute top-2 left-2 h-28 w-28 animate-[spin_6s_linear_reverse_infinite] rounded-full border opacity-50",
              isPlana ? "border-rose-600" : "border-blue-400"
          )}></div>
          <div className={cn(
              "absolute top-1/2 left-1/2 h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-full shadow-[0_0_15px]",
              isPlana ? "bg-rose-600 shadow-rose-600" : "bg-blue-500 shadow-blue-500"
          )}></div>
        </div>
        )}

        {step < 4 ? (
        <div className="mt-8 text-center relative z-10">
          <span className={cn(
              "px-4 py-1 text-[10px] font-black uppercase tracking-[0.2em] rounded-full shadow-lg",
              isPlana ? "bg-rose-900/40 text-rose-400 shadow-rose-900/20" : "bg-blue-500 text-white shadow-blue-200"
          )}>
            Phase 0{step}: {step === 1 ? 'Identification' : step === 2 ? 'Memory Sync' : 'Personality Profile'}
          </span>
          <h1 className={cn("text-3xl font-extrabold mt-6 tracking-tight", isPlana ? "text-slate-100" : "text-slate-800")}>
             {step === 1 ? 'System Initialization' : step === 2 ? 'Synchronization' : 'Neural Calibration'}
          </h1>
          <p className={cn("mt-2 font-medium", isPlana ? "text-slate-400" : "text-slate-500")}>
             {step === 1 ? 'Synchronizing neural pathways with the user...' : step === 2 ? 'Connecting knowledge nodes to the neural core...' : 'Fine-tuning the unit\'s behavioral patterns...'}
          </p>
        </div>
        ) : (
            <div className="mt-8 text-center relative z-10 flex flex-col items-center">
                 <div className="relative w-32 h-32 mb-6">
                    <div className={cn("absolute inset-0 border-[3px] border-dashed rounded-full animate-[spin_15s_linear_infinite] opacity-40", isPlana ? "border-rose-700" : "border-blue-300")}></div>
                    <div className={cn("absolute inset-2 border-2 rounded-full animate-[spin_8s_linear_reverse_infinite] shadow-[0_0_30px]", isPlana ? "border-rose-600 shadow-rose-900/30" : "border-blue-400 shadow-blue-500/30")}></div>
                    <div className={cn("absolute inset-0 rounded-full border-[6px] border-transparent animate-[spin_2s_cubic-bezier(0.76,0,0.24,1)_infinite]", isPlana ? "border-t-rose-500" : "border-t-blue-500")}></div>
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                        <span className={cn("text-xl font-black tracking-tighter", isPlana ? "text-rose-500" : "text-blue-600")}>100%</span>
                    </div>
                 </div>
                 <div className={cn("inline-flex items-center space-x-2 px-4 py-1.5 border rounded-full shadow-sm mb-4", isPlana ? "bg-[#0d1117] border-rose-900/30" : "bg-white border-blue-100")}>
                    <span className="relative flex h-2 w-2">
                    <span className={cn("animate-ping absolute inline-flex h-full w-full rounded-full opacity-75", isPlana ? "bg-rose-500" : "bg-blue-400")}></span>
                    <span className={cn("relative inline-flex rounded-full h-2 w-2", isPlana ? "bg-rose-600" : "bg-blue-500")}></span>
                    </span>
                    <span className={cn("text-[10px] font-bold uppercase tracking-widest", isPlana ? "text-slate-400" : "text-slate-500")}>Modules Deployed</span>
                </div>
                 <h1 className={cn("text-3xl font-extrabold tracking-tight", isPlana ? "text-slate-100" : "text-slate-800")}>Setup Complete</h1>
                 <p className={cn("mt-2 font-medium", isPlana ? "text-slate-400" : "text-slate-500")}>Welcome to your workspace, Sensei.</p>
            </div>
        )}

        <div className="mt-12 min-h-[350px] relative z-10">
          <AnimatePresence mode="wait" custom={direction}>
            {step === 1 && (
              <motion.div 
                key="step1"
                custom={direction}
                variants={variants}
                initial="enter"
                animate="center"
                exit="exit"
                className="space-y-8"
              >
                <div className="group">
                  <label className={cn("block text-[11px] font-black uppercase tracking-widest mb-3 ml-2", isPlana ? "text-rose-400" : "text-blue-500")}>Director's Designation</label>
                  <div className="relative group/input">
                    <input 
                      type="text" 
                      placeholder="Enter your name..." 
                      value={formData.userName}
                      onChange={(e) => setFormData({...formData, userName: e.target.value})}
                      className={cn(
                          "w-full border-b-2 px-6 py-4 text-sm font-bold transition-all outline-none rounded-t-xl",
                          isPlana 
                            ? "bg-[#0d1117]/60 border-rose-900/30 text-white placeholder:text-slate-600 focus:border-rose-500 focus:bg-[#0d1117]" 
                            : "bg-white/60 border-blue-100 text-slate-800 placeholder:text-slate-300 focus:border-blue-500 focus:bg-white/90"
                      )}
                    />
                    <div className={cn("absolute bottom-0 left-0 w-0 h-0.5 transition-all group-focus-within/input:w-full", isPlana ? "bg-rose-500" : "bg-blue-500")}></div>
                  </div>
                </div>

                <div>
                  <label className={cn("block text-[11px] font-black uppercase tracking-widest mb-4 ml-2", isPlana ? "text-rose-400" : "text-blue-500")}>Agent Specialization</label>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {[
                      { id: 'technical', label: 'Technical Analyst', desc: 'Focused on code, logic, and data structures.', icon: Code },
                      { id: 'research', label: 'Research Assistant', desc: 'Deep dives into documents and information.', icon: BookOpen },
                      { id: 'assistant', label: 'Helpful Assistant', desc: 'Provides general assistance and support.', icon: PenTool },
                      { id: 'generalist', label: 'Generalist', desc: 'Versatile across various tasks and topics.', icon: Zap },
                    ].map((spec) => (
                      <button 
                        key={spec.id}
                        onClick={() => setFormData({...formData, specialization: spec.id})}
                        className={cn(
                            "flex items-start p-5 border-2 rounded-2xl hover:shadow-lg hover:scale-[1.02] transition-all group text-left",
                            isPlana 
                                ? "bg-[#0d1117]/50 border-rose-900/10 hover:border-rose-900/40 hover:shadow-rose-900/10" 
                                : "bg-white/70 border-blue-50 hover:border-blue-300 hover:shadow-blue-100/50",
                            formData.specialization === spec.id && (isPlana ? "border-rose-500 shadow-rose-900/20 bg-[#0d1117]" : "border-blue-500 shadow-blue-200/50 ring-1 ring-blue-500 bg-white")
                        )}
                      >
                        <div className={cn(
                            "w-10 h-10 rounded-lg flex items-center justify-center mr-4 transition-colors",
                            formData.specialization === spec.id 
                                ? (isPlana ? "bg-rose-600 text-white" : "bg-blue-500 text-white")
                                : (isPlana ? "bg-rose-900/20 text-rose-500 group-hover:bg-rose-600 group-hover:text-white" : "bg-blue-100 text-blue-600 group-hover:bg-blue-500 group-hover:text-white")
                            )}>
                          <spec.icon className="h-5 w-5" />
                        </div>
                        <div>
                          <p className={cn("font-bold text-sm", isPlana ? "text-slate-200" : "text-slate-800")}>{spec.label}</p>
                          <p className={cn("text-[11px] mt-1", isPlana ? "text-slate-500" : "text-slate-400")}>{spec.desc}</p>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              </motion.div>
            )}

            {step === 2 && (
              <motion.div 
                key="step2"
                custom={direction}
                variants={variants}
                initial="enter"
                animate="center"
                exit="exit"
                className="space-y-4"
              >
                 <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    {[
                      { id: 'cloud', label: 'Cloud Storage', sub: 'Drive / Dropbox', icon: Cloud },
                      { id: 'repo', label: 'Repositories', sub: 'GitHub / GitLab', icon: Github },
                    ].map((source) => (
                      <button 
                        key={source.id}
                        onClick={() => toggleDataSource(source.id)}
                        className={cn(
                            "group relative overflow-hidden rounded-2xl border-2 p-6 text-left transition-all hover:shadow-lg hover:scale-[1.02]",
                            isPlana 
                                ? "bg-[#0d1117]/50 border-rose-900/10 hover:border-rose-900/40 hover:shadow-rose-900/10" 
                                : "bg-white/70 border-blue-50 hover:border-blue-300 hover:shadow-blue-100/50",
                            formData.dataSources.includes(source.id) && (isPlana ? "border-rose-500 bg-[#0d1117] shadow-rose-900/20" : "border-blue-500 bg-white shadow-blue-200/50")
                        )}
                      >
                        <div className={cn(
                            "mb-4 flex h-10 w-10 items-center justify-center rounded-lg transition-all",
                            formData.dataSources.includes(source.id) 
                                ? (isPlana ? "bg-rose-600 text-white" : "bg-blue-500 text-white")
                                : (isPlana ? "bg-rose-900/20 group-hover:bg-rose-600 group-hover:text-white" : "bg-blue-50 group-hover:bg-blue-500 group-hover:text-white")
                            )}>
                           <source.icon className="h-5 w-5" />
                        </div>
                        <p className={cn("text-sm font-bold", isPlana ? "text-slate-200" : "text-slate-800")}>{source.label}</p>
                        <p className={cn("mt-1 text-[10px] font-bold tracking-tight uppercase", isPlana ? "text-slate-500" : "text-slate-400")}>{source.sub}</p>
                        
                        {formData.dataSources.includes(source.id) && (
                          <div className={cn("absolute top-4 right-4", isPlana ? "text-rose-500" : "text-blue-500")}>
                            <Check className="h-5 w-5" />
                          </div>
                        )}
                        <div className={cn(
                            "absolute bottom-0 left-0 h-1 transition-all duration-500",
                            isPlana ? "bg-rose-500" : "bg-blue-400",
                            formData.dataSources.includes(source.id) ? 'w-full' : 'w-0 group-hover:w-full'
                        )}></div>
                      </button>
                    ))}
                 </div>
                 
                 <button className={cn(
                     "group flex w-full items-center justify-between rounded-2xl border-2 p-6 text-left transition-all hover:shadow-lg hover:scale-[1.02]",
                     isPlana 
                        ? "bg-[#0d1117]/50 border-rose-900/10 hover:border-rose-900/40 hover:shadow-rose-900/10" 
                        : "bg-white/70 border-blue-50 hover:border-blue-300 hover:shadow-blue-100/50"
                 )}>
                    <div className="flex items-center">
                    <div className={cn("mr-4 flex h-10 w-10 items-center justify-center rounded-lg", isPlana ? "bg-rose-900/20" : "bg-blue-100")}>
                        <Cloud className={cn("h-5 w-5", isPlana ? "text-rose-500" : "text-blue-500")} />
                    </div>
                    <div>
                        <p className={cn("text-sm font-bold", isPlana ? "text-slate-200" : "text-slate-800")}>Manual Neural Upload</p>
                        <p className={cn("text-[10px] font-bold tracking-tight uppercase", isPlana ? "text-slate-500" : "text-slate-400")}>PDF, TXT, CSV</p>
                    </div>
                    </div>
                    <span className={cn("text-[10px] font-black group-hover:underline", isPlana ? "text-rose-500" : "text-blue-500")}>BROWSE FILES</span>
                </button>
              </motion.div>
            )}

            {step === 3 && (
              <motion.div 
                key="step3"
                custom={direction}
                variants={variants}
                initial="enter"
                animate="center"
                exit="exit"
                className="space-y-8"
              >
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className={cn("block text-[11px] font-black uppercase tracking-widest mb-2 ml-2", isPlana ? "text-rose-400" : "text-blue-500")}>Agent Name</label>
                    <input 
                      type="text" 
                      placeholder="Designate..." 
                      value={formData.agentName}
                      onChange={(e) => setFormData({...formData, agentName: e.target.value})}
                      className={cn(
                          "w-full border-b-2 px-5 py-3 font-bold outline-none transition-all rounded-t-lg",
                          isPlana 
                            ? "bg-[#0d1117]/60 border-rose-900/30 text-white placeholder:text-slate-600 focus:border-rose-500 focus:bg-[#0d1117]" 
                            : "bg-white/60 border-blue-100 text-slate-800 focus:border-blue-500 focus:bg-white/90"
                      )} 
                    />
                  </div>
                  <div>
                    <label className={cn("block text-[11px] font-black uppercase tracking-widest mb-2 ml-2", isPlana ? "text-rose-400" : "text-blue-500")}>Tone Settings</label>
                    <select 
                      value={formData.tone}
                      onChange={(e) => setFormData({...formData, tone: e.target.value})}
                      className={cn(
                          "w-full border-b-2 px-5 py-3 font-bold outline-none appearance-none cursor-pointer rounded-t-lg",
                          isPlana 
                            ? "bg-[#0d1117]/60 border-rose-900/30 text-white focus:border-rose-400 focus:bg-[#0d1117]" 
                            : "bg-white/60 border-blue-100 text-slate-800 focus:border-blue-400 focus:bg-white/90"
                      )}
                    >
                      <option>Analytical</option>
                      <option>Warm</option>
                      <option>Professional</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className={cn("block text-[11px] font-black uppercase tracking-widest mb-3 ml-2", isPlana ? "text-rose-400" : "text-blue-500")}>Prime Directives</label>
                  <textarea 
                    rows={2}
                    value={formData.directives}
                    onChange={(e) => setFormData({...formData, directives: e.target.value})}
                    placeholder="Ex: Provide code in Python only..." 
                    className={cn(
                        "w-full border-2 rounded-2xl px-5 py-4 font-medium outline-none transition-all resize-none shadow-inner",
                        isPlana 
                            ? "bg-[#0d1117]/60 border-rose-900/30 text-white placeholder:text-slate-600 focus:border-rose-400 focus:bg-[#0d1117]" 
                            : "bg-white/60 border-blue-50 text-slate-800 focus:border-blue-400 focus:bg-white/90"
                    )}
                  ></textarea>
                </div>
              </motion.div>
            )}

            {step === 4 && (
                <motion.div
                    key="step4"
                    custom={direction}
                    variants={variants}
                    initial="enter"
                    animate="center"
                    exit="exit"
                    className="flex flex-col items-center justify-center space-y-6 pt-4"
                >
                     <div className={cn("font-mono text-[10px] space-y-1 opacity-80 uppercase text-center", isPlana ? "text-rose-400/60" : "text-blue-300")}>
                        <p className="animate-pulse">{">>"} ACCESSING SCHALE_NETWORK_PROTOCOL...</p>
                        <p className="delay-75 animate-pulse">{">>"} VERIFYING IDENTITY: SENSEI_AUTHORIZED</p>
                        <p className="delay-150 animate-pulse">{">>"} LOADING AGENT_CORE_V2.0.6...</p>
                    </div>

                    <div className={cn("p-6 rounded-xl border w-full", isPlana ? "bg-rose-900/5 border-rose-900/20" : "bg-blue-50 border-blue-100")}>
                        <h3 className={cn("text-xs font-black uppercase tracking-widest mb-4", isPlana ? "text-rose-500" : "text-blue-500")}>Summary</h3>
                        <div className={cn("space-y-2 text-sm", isPlana ? "text-slate-400" : "text-slate-600")}>
                             <div className={cn("flex justify-between border-b pb-2", isPlana ? "border-rose-900/20" : "border-blue-100")}>
                                <span className="font-bold">Director</span>
                                <span>{formData.userName || "Unknown"}</span>
                             </div>
                             <div className={cn("flex justify-between border-b pb-2", isPlana ? "border-rose-900/20" : "border-blue-100")}>
                                <span className="font-bold">Agent Name</span>
                                <span>{formData.agentName || "Arona"}</span>
                             </div>
                             <div className={cn("flex justify-between border-b pb-2", isPlana ? "border-rose-900/20" : "border-blue-100")}>
                                <span className="font-bold">Specialization</span>
                                <span className="capitalize">{formData.specialization || "General"}</span>
                             </div>
                        </div>
                    </div>
                </motion.div>
            )}
          </AnimatePresence>
        </div>

        <div className="mt-12 flex justify-between items-center relative z-10">

          <button 
            onClick={handleBack} 
            className={cn(
                "text-xs font-black uppercase tracking-widest hover:text-slate-500",
                (step === 1 || step === 4) ? 'invisible' : '',
                isPlana ? "text-slate-500" : "text-slate-300"
            )}
          >
            Back
          </button>
          
          <div className="flex items-center space-x-6">
            {step === 2 && (
                <button 
                  onClick={handleNext} 
                  className={cn(
                      "text-[10px] font-black uppercase tracking-[0.2em] transition-colors",
                      isPlana ? "text-slate-500 hover:text-rose-400" : "text-slate-300 hover:text-blue-400"
                  )}
                >
                    Skip for now
                </button>
            )}
            <button 
              onClick={handleNext}
              className={cn(
                  "px-10 py-4 font-black rounded-2xl shadow-xl transition-all flex items-center group active:scale-95",
                  isPlana 
                    ? "bg-rose-600 hover:bg-rose-500 text-white shadow-rose-900/20" 
                    : "bg-blue-500 hover:bg-blue-600 text-white shadow-blue-200"
              )}
            >
              {step === 1 ? 'Confirm Identity' : step === 2 ? 'Sync Data' : step === 3 ? 'Finalize Build' : 'Enter Workspace'}
              {step === 4 ? <Zap className="ml-2 h-4 w-4 fill-white" /> : <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />}
            </button>
          </div>
        </div>

        {/* Footers */}
        <div className={cn("mt-12 text-[10px] font-mono uppercase tracking-[0.4em] opacity-60 text-center", isPlana ? "text-rose-400" : "text-blue-300")}>
            {step === 1 && "System Status: Ready // Authentication: Verified"}
            {step === 2 && "Memory: Syncing // Awaiting_Data"}
            {step === 3 && "Good day to you, Sensei! // 先生、こんにちは！"}
        </div>
      </div>
    </div>
  );
}
