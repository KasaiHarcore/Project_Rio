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

export default function OnboardingPage() {
  const router = useRouter();
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
    <div className="flex min-h-screen flex-col items-center justify-center bg-[linear-gradient(135deg,_#fdfeff_0%,_#e3f2fd_100%)] p-4 font-sans text-slate-700">
      {/* Progress Bar */}
      <div className="fixed top-0 left-0 w-full h-1 bg-white">
        <motion.div 
          className="h-full bg-blue-400 shadow-[0_0_10px_#60a5fa]" 
          initial={{ width: "33%" }}
          animate={{ width: step === 4 ? "100%" : `${step * 33.33}%` }}
          transition={{ duration: 0.5 }}
        />
      </div>

      <div className="w-full max-w-2xl bg-white/40 backdrop-blur-md border border-blue-100 rounded-[2rem] p-8 md:p-12 shadow-2xl relative overflow-hidden">
        
        {/* Header decoration */}
        <div className="absolute top-8 right-10 text-right hidden md:block">
          <span className="block font-mono text-[10px] text-blue-300">
            {step === 1 ? 'LINK_STATUS: READY' : step === 2 ? 'SYNCHRONIZE_STATUS: READY' : step === 3 ? 'ENCRYPTION: AES-256' : 'SYSTEM: ONLINE'}
          </span>
          <span className="block font-mono text-[10px] tracking-tighter text-blue-400">
             {step === 1 ? 'BITRATE: -- MBPS' : step === 2 ? 'BITRATE: 1024 MBPS' : step === 3 ? 'CALIBRATION_ACTIVE' : 'CONNECTED'}
          </span>
        </div>

        {/* Floating Halo Animation */}
        {step < 4 && (
        <div className="absolute -top-16 left-1/2 -translate-x-1/2">
          <div className="h-32 w-32 animate-[spin_10s_linear_infinite] rounded-full border-2 border-dashed border-blue-300 opacity-30"></div>
          <div className="absolute top-2 left-2 h-28 w-28 animate-[spin_6s_linear_reverse_infinite] rounded-full border border-blue-400 opacity-50"></div>
          <div className="absolute top-1/2 left-1/2 h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-full bg-blue-500 shadow-[0_0_15px_#3b82f6]"></div>
        </div>
        )}

        {step < 4 ? (
        <div className="mt-8 text-center relative z-10">
          <span className="px-4 py-1 bg-blue-500 text-white text-[10px] font-black uppercase tracking-[0.2em] rounded-full shadow-lg shadow-blue-200">
            Phase 0{step}: {step === 1 ? 'Identification' : step === 2 ? 'Memory Sync' : 'Personality Profile'}
          </span>
          <h1 className="text-3xl font-extrabold text-slate-800 mt-6 tracking-tight">
             {step === 1 ? 'System Initialization' : step === 2 ? 'Synchronization' : 'Neural Calibration'}
          </h1>
          <p className="text-slate-500 mt-2 font-medium">
             {step === 1 ? 'Synchronizing neural pathways with the user...' : step === 2 ? 'Connecting knowledge nodes to the neural core...' : 'Fine-tuning the unit\'s behavioral patterns...'}
          </p>
        </div>
        ) : (
            <div className="mt-8 text-center relative z-10 flex flex-col items-center">
                 <div className="relative w-32 h-32 mb-6">
                    <div className="absolute inset-0 border-[3px] border-dashed border-blue-300 rounded-full animate-[spin_15s_linear_infinite] opacity-40"></div>
                    <div className="absolute inset-2 border-2 border-blue-400 rounded-full animate-[spin_8s_linear_reverse_infinite] shadow-[0_0_30px_rgba(59,130,246,0.3)]"></div>
                    <div className="absolute inset-0 rounded-full border-[6px] border-transparent border-t-blue-500 animate-[spin_2s_cubic-bezier(0.76,0,0.24,1)_infinite]"></div>
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                        <span className="text-xl font-black text-blue-600 tracking-tighter">100%</span>
                    </div>
                 </div>
                 <div className="inline-flex items-center space-x-2 px-4 py-1.5 bg-white border border-blue-100 rounded-full shadow-sm mb-4">
                    <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
                    </span>
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Modules Deployed</span>
                </div>
                 <h1 className="text-3xl font-extrabold text-slate-800 tracking-tight">Setup Complete</h1>
                 <p className="text-slate-500 mt-2 font-medium">Welcome to your workspace, Sensei.</p>
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
                  <label className="block text-[11px] font-black text-blue-500 uppercase tracking-widest mb-3 ml-2">Director's Designation</label>
                  <div className="relative group/input">
                    <input 
                      type="text" 
                      placeholder="Enter your name..." 
                      value={formData.userName}
                      onChange={(e) => setFormData({...formData, userName: e.target.value})}
                      className="w-full bg-white/60 border-b-2 border-blue-100 px-6 py-4 text-sm font-bold focus:border-blue-500 focus:bg-white/90 transition-all outline-none placeholder:text-slate-300 rounded-t-xl" 
                    />
                    <div className="absolute bottom-0 left-0 w-0 h-0.5 bg-blue-500 transition-all group-focus-within/input:w-full"></div>
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] font-black text-blue-500 uppercase tracking-widest mb-4 ml-2">Agent Specialization</label>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {[
                      { id: 'technical', label: 'Technical Analyst', desc: 'Focused on code, logic, and data structures.', icon: Code },
                      { id: 'creative', label: 'Creative Assistant', desc: 'Specialized in design, ideation and writing.', icon: PenTool },
                      { id: 'research', label: 'Research Partner', desc: 'Optimized for data synthesis and fact-checking.', icon: BookOpen },
                    ].map((spec) => (
                      <button 
                        key={spec.id}
                        onClick={() => setFormData({...formData, specialization: spec.id})}
                        className={`flex items-start p-5 bg-white/70 border-2 rounded-2xl hover:border-blue-300 hover:shadow-lg hover:shadow-blue-100/50 hover:scale-[1.02] transition-all group text-left ${formData.specialization === spec.id ? 'border-blue-500 shadow-xl shadow-blue-200/50 ring-1 ring-blue-500 bg-white' : 'border-blue-50'}`}
                      >
                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center mr-4 transition-colors ${formData.specialization === spec.id ? 'bg-blue-500 text-white' : 'bg-blue-100 text-blue-600 group-hover:bg-blue-500 group-hover:text-white'}`}>
                          <spec.icon className="h-5 w-5" />
                        </div>
                        <div>
                          <p className="font-bold text-slate-800 text-sm">{spec.label}</p>
                          <p className="text-[11px] text-slate-400 mt-1">{spec.desc}</p>
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
                      { id: 'local', label: 'Local Archives', sub: 'Documents / PDFs', icon: HardDrive },
                    ].map((source) => (
                      <button 
                        key={source.id}
                        onClick={() => toggleDataSource(source.id)}
                        className={`group relative overflow-hidden rounded-2xl border-2 bg-white/70 p-6 text-left transition-all hover:border-blue-300 hover:shadow-lg hover:shadow-blue-100/50 hover:scale-[1.02] ${formData.dataSources.includes(source.id) ? 'border-blue-500 bg-white shadow-xl shadow-blue-200/50' : 'border-blue-50'}`}
                      >
                        <div className={`mb-4 flex h-10 w-10 items-center justify-center rounded-lg transition-all ${formData.dataSources.includes(source.id) ? 'bg-blue-500 text-white' : 'bg-blue-50 group-hover:bg-blue-500 group-hover:text-white'}`}>
                           <source.icon className="h-5 w-5" />
                        </div>
                        <p className="text-sm font-bold text-slate-800">{source.label}</p>
                        <p className="mt-1 text-[10px] font-bold tracking-tight text-slate-400 uppercase">{source.sub}</p>
                        
                        {formData.dataSources.includes(source.id) && (
                          <div className="absolute top-4 right-4 text-blue-500">
                            <Check className="h-5 w-5" />
                          </div>
                        )}
                        <div className={`absolute bottom-0 left-0 h-1 bg-blue-400 transition-all duration-500 ${formData.dataSources.includes(source.id) ? 'w-full' : 'w-0 group-hover:w-full'}`}></div>
                      </button>
                    ))}
                 </div>
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
                    <label className="block text-[11px] font-black text-blue-500 uppercase tracking-widest mb-2 ml-2">Agent Name</label>
                    <input 
                      type="text" 
                      placeholder="Designate..." 
                      value={formData.agentName}
                      onChange={(e) => setFormData({...formData, agentName: e.target.value})}
                      className="w-full bg-white/60 border-b-2 border-blue-100 px-5 py-3 font-bold focus:border-blue-500 focus:bg-white/90 outline-none transition-all rounded-t-lg" 
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-black text-blue-500 uppercase tracking-widest mb-2 ml-2">Tone Settings</label>
                    <select 
                      value={formData.tone}
                      onChange={(e) => setFormData({...formData, tone: e.target.value})}
                      className="w-full bg-white/60 border-b-2 border-blue-100 px-5 py-3 font-bold outline-none focus:border-blue-400 focus:bg-white/90 appearance-none cursor-pointer rounded-t-lg"
                    >
                      <option>Analytical</option>
                      <option>Warm</option>
                      <option>Professional</option>
                      <option>Tsundere</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] font-black text-blue-500 uppercase tracking-widest mb-3 ml-2">Prime Directives</label>
                  <textarea 
                    rows={4}
                    value={formData.directives}
                    onChange={(e) => setFormData({...formData, directives: e.target.value})}
                    placeholder="Ex: Provide code in Python only..." 
                    className="w-full bg-white/60 border-2 border-blue-50 rounded-2xl px-5 py-4 font-medium focus:border-blue-400 focus:bg-white/90 outline-none transition-all resize-none shadow-inner"
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
                     <div className="font-mono text-[10px] text-blue-300 space-y-1 opacity-80 uppercase text-center">
                        <p className="animate-pulse">{">>"} ACCESSING SCHALE_NETWORK_PROTOCOL...</p>
                        <p className="delay-75 animate-pulse">{">>"} VERIFYING IDENTITY: SENSEI_AUTHORIZED</p>
                        <p className="delay-150 animate-pulse">{">>"} LOADING AGENT_CORE_V2.0.6...</p>
                    </div>

                    <div className='p-6 bg-blue-50 rounded-xl border border-blue-100 w-full'>
                        <h3 className="text-xs font-black text-blue-500 uppercase tracking-widest mb-4">Summary</h3>
                        <div className="space-y-2 text-sm text-slate-600">
                             <div className="flex justify-between border-b pb-2 border-blue-100">
                                <span className="font-bold">Director</span>
                                <span>{formData.userName || "Unknown"}</span>
                             </div>
                             <div className="flex justify-between border-b pb-2 border-blue-100">
                                <span className="font-bold">Agent Name</span>
                                <span>{formData.agentName || "Arona"}</span>
                             </div>
                             <div className="flex justify-between border-b pb-2 border-blue-100">
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
            className={`text-xs font-black text-slate-300 uppercase tracking-widest hover:text-slate-500 ${(step === 1 || step === 4) ? 'invisible' : ''}`}
          >
            Back
          </button>
          
          <button 
            onClick={handleNext}
            className="px-10 py-4 bg-blue-500 hover:bg-blue-600 text-white font-black rounded-2xl shadow-xl shadow-blue-200 transition-all flex items-center group"
          >
            {step === 3 ? 'Initialize' : step === 4 ? 'Enter Workspace' : 'Next Phase'}
            {step === 4 ? <Zap className="ml-2 h-4 w-4 fill-white" /> : <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />}
          </button>
        </div>

      </div>
    </div>
  );
}
