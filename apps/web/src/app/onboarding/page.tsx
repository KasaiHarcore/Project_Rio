'use client';

import { useState, useRef } from 'react';
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
  Zap,
  Loader2,
  Upload,
  File,
  X
} from 'lucide-react';
import { cn } from '@/shared/lib/utils';
import { apiSaveOnboarding } from '@/features/onboarding/api';
import { apiUploadDocument } from '@/features/knowledge/api';

export default function OnboardingPage() {
  const router = useRouter();

  const [step, setStep] = useState(1);
  const [direction, setDirection] = useState(0);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState({
    userName: '',
    specialization: '',
    dataSources: [] as string[],
    agentName: '',
    tone: 'Professional',
    directives: ''
  });

  // File upload state
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadedFiles, setUploadedFiles] = useState<{ name: string; size: number }[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const handleFileUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    setUploadError(null);
    const newFiles: { name: string; size: number }[] = [];
    for (const file of Array.from(files)) {
      try {
        await apiUploadDocument(file);
        newFiles.push({ name: file.name, size: file.size });
      } catch (err) {
        setUploadError(`Failed to upload ${file.name}`);
      }
    }
    if (newFiles.length > 0) {
      setUploadedFiles(prev => [...prev, ...newFiles]);
      if (!formData.dataSources.includes('local')) {
        setFormData(prev => ({ ...prev, dataSources: [...prev.dataSources, 'local'] }));
      }
    }
    setUploading(false);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

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

  const handleNext = async () => {
    if (step < 4) {
      setDirection(1);
      setStep(step + 1);
    } else {
      // Save onboarding data then navigate
      try {
        setSaving(true);
        await apiSaveOnboarding({
          user_name: formData.userName || undefined,
          specialization: formData.specialization || undefined,
          data_sources: formData.dataSources,
          agent_name: formData.agentName || undefined,
          tone: formData.tone || undefined,
          directives: formData.directives || undefined,
        });
      } catch {
      } finally {
        setSaving(false);
      }
      // First-time user: skip splash screen and ensure tutorial triggers
      try {
        localStorage.setItem('schale-splash-seen', 'true');
        localStorage.removeItem('schale-tutorial-completed');
      } catch {}
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
    <div className="flex min-h-screen flex-col items-center justify-center p-4 font-sans transition-colors bg-[#0d1117] text-slate-200">
      {/* Progress Bar */}
      <div className="fixed top-0 left-0 w-full h-1 bg-slate-900">
        <motion.div 
          className="h-full shadow-[0_0_10px] bg-rose-600 shadow-rose-900/50"
          initial={{ width: "33%" }}
          animate={{ width: step === 4 ? "100%" : `${step * 33.33}%` }}
          transition={{ duration: 0.5 }}
        />
      </div>

      <div className="w-full max-w-2xl backdrop-blur-md border rounded-[2rem] p-8 md:p-12 shadow-2xl relative overflow-hidden transition-all bg-[#161b22]/80 border-rose-900/30 shadow-none">
        
        {/* Header decoration */}
        <div className="absolute top-8 right-10 text-right hidden md:block">
          <span className="block font-mono text-[10px] text-rose-400/60">
            {step === 1 ? 'LINK_STATUS: READY' : step === 2 ? 'SYNCHRONIZE_STATUS: READY' : step === 3 ? 'ENCRYPTION: AES-256' : 'SYSTEM: ONLINE'}
          </span>
          <span className="block font-mono text-[10px] tracking-tighter text-rose-500">
             {step === 1 ? 'BITRATE: -- MBPS' : step === 2 ? 'BITRATE: 1024 MBPS' : step === 3 ? 'CALIBRATION_ACTIVE' : 'CONNECTED'}
          </span>
        </div>

        {/* Floating Halo Animation */}
        {step < 4 && (
        <div className="absolute -top-16 left-1/2 -translate-x-1/2">
          <div className="h-32 w-32 animate-[spin_10s_linear_infinite] rounded-full border-2 border-dashed opacity-30 border-rose-700"></div>
          <div className="absolute top-2 left-2 h-28 w-28 animate-[spin_6s_linear_reverse_infinite] rounded-full border opacity-50 border-rose-600"></div>
          <div className="absolute top-1/2 left-1/2 h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-full shadow-[0_0_15px] bg-rose-600 shadow-rose-600"></div>
        </div>
        )}

        {step < 4 ? (
        <div className="mt-8 text-center relative z-10">
          <span className="px-4 py-1 text-[10px] font-black uppercase tracking-[0.2em] rounded-full shadow-lg bg-rose-900/40 text-rose-400 shadow-rose-900/20">
            Phase 0{step}: {step === 1 ? 'Identification' : step === 2 ? 'Memory Sync' : 'Personality Profile'}
          </span>
          <h1 className="text-3xl font-extrabold mt-6 tracking-tight text-slate-100">
             {step === 1 ? 'System Initialization' : step === 2 ? 'Synchronization' : 'Neural Calibration'}
          </h1>
          <p className="mt-2 font-medium text-slate-400">
             {step === 1 ? 'Synchronizing neural pathways with the user...' : step === 2 ? 'Connecting knowledge nodes to the neural core...' : 'Fine-tuning the unit\'s behavioral patterns...'}
          </p>
        </div>
        ) : (
            <div className="mt-8 text-center relative z-10 flex flex-col items-center">
                 <div className="relative w-32 h-32 mb-6">
                    <div className="absolute inset-0 border-[3px] border-dashed rounded-full animate-[spin_15s_linear_infinite] opacity-40 border-rose-700"></div>
                    <div className="absolute inset-2 border-2 rounded-full animate-[spin_8s_linear_reverse_infinite] shadow-[0_0_30px] border-rose-600 shadow-rose-900/30"></div>
                    <div className="absolute inset-0 rounded-full border-[6px] border-transparent animate-[spin_2s_cubic-bezier(0.76,0,0.24,1)_infinite] border-t-rose-500"></div>
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                        <span className="text-xl font-black tracking-tighter text-rose-500">100%</span>
                    </div>
                 </div>
                 <div className="inline-flex items-center space-x-2 px-4 py-1.5 border rounded-full shadow-sm mb-4 bg-[#0d1117] border-rose-900/30">
                    <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 bg-rose-500"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-600"></span>
                    </span>
                    <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Modules Deployed</span>
                </div>
                 <h1 className="text-3xl font-extrabold tracking-tight text-slate-100">Setup Complete</h1>
                 <p className="mt-2 font-medium text-slate-400">Welcome to your workspace, Sensei.</p>
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
                  <label className="block text-[11px] font-black uppercase tracking-widest mb-3 ml-2 text-rose-400">Director's Designation</label>
                  <div className="relative group/input">
                    <input 
                      type="text" 
                      placeholder="Enter your name..." 
                      value={formData.userName}
                      onChange={(e) => setFormData({...formData, userName: e.target.value})}
                      className="w-full border-b-2 px-6 py-4 text-sm font-bold transition-all outline-none rounded-t-xl bg-[#0d1117]/60 border-rose-900/30 text-white placeholder:text-slate-600 focus:border-rose-500 focus:bg-[#0d1117]"
                    />
                    <div className="absolute bottom-0 left-0 w-0 h-0.5 transition-all group-focus-within/input:w-full bg-rose-500"></div>
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] font-black uppercase tracking-widest mb-4 ml-2 text-rose-400">Agent Specialization</label>
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
                            "bg-[#0d1117]/50 border-rose-900/10 hover:border-rose-900/40 hover:shadow-rose-900/10",
                            formData.specialization === spec.id && "border-rose-500 shadow-rose-900/20 bg-[#0d1117]"
                        )}
                      >
                        <div className={cn(
                            "w-10 h-10 rounded-lg flex items-center justify-center mr-4 transition-colors",
                            formData.specialization === spec.id
                                ? "bg-rose-600 text-white"
                                : "bg-rose-900/20 text-rose-500 group-hover:bg-rose-600 group-hover:text-white"
                            )}>
                          <spec.icon className="h-5 w-5" />
                        </div>
                        <div>
                          <p className="font-bold text-sm text-slate-200">{spec.label}</p>
                          <p className="text-[11px] mt-1 text-slate-500">{spec.desc}</p>
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
                            "bg-[#0d1117]/50 border-rose-900/10 hover:border-rose-900/40 hover:shadow-rose-900/10",
                            formData.dataSources.includes(source.id) && "border-rose-500 bg-[#0d1117] shadow-rose-900/20"
                        )}
                      >
                        <div className={cn(
                            "mb-4 flex h-10 w-10 items-center justify-center rounded-lg transition-all",
                            formData.dataSources.includes(source.id)
                                ? "bg-rose-600 text-white"
                                : "bg-rose-900/20 group-hover:bg-rose-600 group-hover:text-white"
                            )}>
                           <source.icon className="h-5 w-5" />
                        </div>
                        <p className="text-sm font-bold text-slate-200">{source.label}</p>
                        <p className="mt-1 text-[10px] font-bold tracking-tight uppercase text-slate-500">{source.sub}</p>
                        
                        {formData.dataSources.includes(source.id) && (
                          <div className="absolute top-4 right-4 text-rose-500">
                            <Check className="h-5 w-5" />
                          </div>
                        )}
                        <div className={cn(
                            "absolute bottom-0 left-0 h-1 transition-all duration-500",
                            "bg-rose-500",
                            formData.dataSources.includes(source.id) ? 'w-full' : 'w-0 group-hover:w-full'
                        )}></div>
                      </button>
                    ))}
                 </div>
                 
                 <input
                   ref={fileInputRef}
                   type="file"
                   multiple
                   accept=".pdf,.txt,.csv,.json,.html,.md,.docx"
                   className="hidden"
                   onChange={(e) => handleFileUpload(e.target.files)}
                 />
                 <button
                   onClick={() => fileInputRef.current?.click()}
                   disabled={uploading}
                   className={cn(
                     "group flex w-full items-center justify-between rounded-2xl border-2 p-6 text-left transition-all hover:shadow-lg hover:scale-[1.02]",
                     "bg-[#0d1117]/50 border-rose-900/10 hover:border-rose-900/40 hover:shadow-rose-900/10",
                     uploadedFiles.length > 0 && "border-rose-500 bg-[#0d1117] shadow-rose-900/20"
                 )}>
                    <div className="flex items-center">
                    <div className={cn("mr-4 flex h-10 w-10 items-center justify-center rounded-lg",
                      uploadedFiles.length > 0
                        ? "bg-rose-600 text-white"
                        : "bg-rose-900/20"
                    )}>
                        {uploading ? <Loader2 className="h-5 w-5 animate-spin text-rose-500" /> : <Upload className="h-5 w-5 text-rose-500" />}
                    </div>
                    <div>
                        <p className="text-sm font-bold text-slate-200">
                          {uploading ? 'Uploading...' : 'Manual Neural Upload'}
                        </p>
                        <p className="text-[10px] font-bold tracking-tight uppercase text-slate-500">
                          {uploadedFiles.length > 0 ? `${uploadedFiles.length} file${uploadedFiles.length > 1 ? 's' : ''} uploaded` : 'PDF, TXT, CSV, JSON, HTML, MD, DOCX'}
                        </p>
                    </div>
                    </div>
                    <span className="text-[10px] font-black group-hover:underline text-rose-500">
                      {uploading ? '' : 'BROWSE FILES'}
                    </span>
                    {uploadedFiles.length > 0 && (
                      <div className="absolute top-4 right-4 text-rose-500">
                        <Check className="h-5 w-5" />
                      </div>
                    )}
                </button>

                {/* Uploaded file list */}
                {uploadedFiles.length > 0 && (
                  <div className="rounded-xl border p-3 space-y-2 mt-2 bg-[#0d1117]/50 border-rose-900/20">
                    {uploadedFiles.map((f, i) => (
                      <div key={i} className="flex items-center justify-between text-xs px-2 py-1.5 rounded-lg bg-rose-900/10">
                        <div className="flex items-center gap-2 truncate">
                          <File className="h-3.5 w-3.5 flex-shrink-0 text-rose-400" />
                          <span className="font-medium truncate text-slate-300">{f.name}</span>
                        </div>
                        <span className="text-[10px] ml-2 flex-shrink-0 text-slate-500">
                          {f.size < 1024 ? `${f.size} B` : f.size < 1048576 ? `${(f.size / 1024).toFixed(1)} KB` : `${(f.size / 1048576).toFixed(1)} MB`}
                        </span>
                      </div>
                    ))}
                  </div>
                )}

                {uploadError && (
                  <p className="text-xs mt-2 ml-2 text-rose-400">{uploadError}</p>
                )}
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
                    <label className="block text-[11px] font-black uppercase tracking-widest mb-2 ml-2 text-rose-400">Agent Name</label>
                    <input 
                      type="text" 
                      placeholder="Designate..." 
                      value={formData.agentName}
                      onChange={(e) => setFormData({...formData, agentName: e.target.value})}
                      className="w-full border-b-2 px-5 py-3 font-bold outline-none transition-all rounded-t-lg bg-[#0d1117]/60 border-rose-900/30 text-white placeholder:text-slate-600 focus:border-rose-500 focus:bg-[#0d1117]" 
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-black uppercase tracking-widest mb-2 ml-2 text-rose-400">Tone Settings</label>
                    <select 
                      value={formData.tone}
                      onChange={(e) => setFormData({...formData, tone: e.target.value})}
                      className="w-full border-b-2 px-5 py-3 font-bold outline-none appearance-none cursor-pointer rounded-t-lg bg-[#0d1117]/60 border-rose-900/30 text-white focus:border-rose-400 focus:bg-[#0d1117]"
                    >
                      <option className="bg-[#0d1117] text-white">Analytical</option>
                      <option className="bg-[#0d1117] text-white">Warm</option>
                      <option className="bg-[#0d1117] text-white">Professional</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] font-black uppercase tracking-widest mb-3 ml-2 text-rose-400">Prime Directives</label>
                  <textarea 
                    rows={2}
                    value={formData.directives}
                    onChange={(e) => setFormData({...formData, directives: e.target.value})}
                    placeholder="Ex: Provide code in Python only..." 
                    className="w-full border-2 rounded-2xl px-5 py-4 font-medium outline-none transition-all resize-none shadow-inner bg-[#0d1117]/60 border-rose-900/30 text-white placeholder:text-slate-600 focus:border-rose-400 focus:bg-[#0d1117]"
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
                     <div className="font-mono text-[10px] space-y-1 opacity-80 uppercase text-center text-rose-400/60">
                        <p className="animate-pulse">{">>"} ACCESSING SCHALE_NETWORK_PROTOCOL...</p>
                        <p className="delay-75 animate-pulse">{">>"} VERIFYING IDENTITY: SENSEI_AUTHORIZED</p>
                        <p className="delay-150 animate-pulse">{">>"} LOADING AGENT_CORE_V2.0.6...</p>
                    </div>

                    <div className="p-6 rounded-xl border w-full bg-rose-900/5 border-rose-900/20">
                        <h3 className="text-xs font-black uppercase tracking-widest mb-4 text-rose-500">Summary</h3>
                        <div className="space-y-2 text-sm text-slate-400">
                             <div className="flex justify-between border-b pb-2 border-rose-900/20">
                                <span className="font-bold">Director</span>
                                <span>{formData.userName || "Unknown"}</span>
                             </div>
                             <div className="flex justify-between border-b pb-2 border-rose-900/20">
                                <span className="font-bold">Agent Name</span>
                                <span>{formData.agentName || "Rio"}</span>
                             </div>
                             <div className="flex justify-between border-b pb-2 border-rose-900/20">
                                <span className="font-bold">Specialization</span>
                                <span className="capitalize">{formData.specialization || "General"}</span>
                             </div>
                             <div className="flex justify-between border-b pb-2 border-rose-900/20">
                                <span className="font-bold">Data Sources</span>
                                <span className="capitalize">{[...formData.dataSources.filter(s => s !== 'local').map(s => s === 'repo' ? 'GitHub' : s === 'cloud' ? 'Cloud' : s), ...(uploadedFiles.length > 0 ? [`${uploadedFiles.length} file${uploadedFiles.length > 1 ? 's' : ''}`] : [])].join(', ') || "None"}</span>
                             </div>
                             <div className="flex justify-between border-b pb-2 border-rose-900/20">
                                <span className="font-bold">Tone</span>
                                <span>{formData.tone || "Professional"}</span>
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
                "text-slate-500"
            )}
          >
            Back
          </button>
          
          <div className="flex items-center space-x-6">
            {step === 2 && (
                <button 
                  onClick={handleNext} 
                  className="text-[10px] font-black uppercase tracking-[0.2em] transition-colors text-slate-500 hover:text-rose-400"
                >
                    Skip for now
                </button>
            )}
            <button 
              onClick={handleNext}
              disabled={saving}
              className="px-10 py-4 font-black rounded-2xl shadow-xl transition-all flex items-center group active:scale-95 disabled:opacity-60 disabled:cursor-not-allowed bg-rose-600 hover:bg-rose-500 text-white shadow-rose-900/20"
            >
              {saving ? 'Saving…' : step === 1 ? 'Confirm Identity' : step === 2 ? 'Sync Data' : step === 3 ? 'Finalize Build' : 'Enter Workspace'}
              {saving ? <Loader2 className="ml-2 h-4 w-4 animate-spin" /> : step === 4 ? <Zap className="ml-2 h-4 w-4 fill-white" /> : <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />}
            </button>
          </div>
        </div>

        {/* Footers */}
        <div className="mt-12 text-[10px] font-mono uppercase tracking-[0.4em] opacity-60 text-center text-rose-400">
            {step === 1 && "System Status: Ready // Authentication: Verified"}
            {step === 2 && "Memory: Syncing // Awaiting_Data"}
            {step === 3 && "Good day to you, Sensei! // 先生、こんにちは！"}
        </div>
      </div>
    </div>
  );
}
