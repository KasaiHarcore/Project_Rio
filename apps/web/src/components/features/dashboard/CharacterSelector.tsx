import React, { useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CHARACTERS, CharacterId } from '@/types/character'
import { useUIStore } from '@/store/ui-store'
import { cn } from '@/lib/utils'
import { Check } from 'lucide-react'
import { useTheme } from '@/components/providers/theme-provider'
import { getCycleConfig } from '@/lib/cycle-config'

export function CharacterSelector() {
  const activeCharacterId = useUIStore((state) => state.activeCharacterId)
  const setActiveCharacter = useUIStore((state) => state.setActiveCharacter)
  const [isOpen, setIsOpen] = React.useState(false)
  
  const { theme } = useTheme()
  const config = getCycleConfig(theme)

  // Sync Character with Theme automatically
  useEffect(() => {
    if (activeCharacterId !== config.characterId) {
        setActiveCharacter(config.characterId as CharacterId)
    }
  }, [theme, config.characterId, setActiveCharacter, activeCharacterId])

  // Always use the store's active character for display, which is now synced
  const activeChar = CHARACTERS.find(c => c.id === activeCharacterId) || CHARACTERS[0]
  const isNight = theme === 'dark'

  return (
    <div className="relative z-50">
      {/* Trigger Button */}
      <motion.button
        onClick={() => setIsOpen(!isOpen)}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        className={cn(
          "flex items-center gap-3 pl-2 pr-4 py-2 rounded-full border transition-all duration-300 backdrop-blur-md shadow-sm",
          isNight 
            ? "bg-rose-900/40 border-rose-500/30 text-rose-200 hover:border-rose-400 hover:bg-rose-900/60" 
            : "bg-blue-50/80 border-blue-200 hover:border-blue-300 text-blue-900"
        )}
      >
        <div className={cn(
          "w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white shadow-inner",
          isNight ? "bg-rose-600" : "bg-blue-400"
        )}>
          {activeChar.name[0]}
        </div>
        <div className="text-left hidden sm:block">
          <div className={cn("text-xs font-bold uppercase tracking-wider opacity-70", isNight ? "text-rose-300" : "text-blue-900")}>Assistant</div>
          <div className="text-sm font-black leading-none">{activeChar.name}</div>
        </div>
      </motion.button>


      {/* Dropdown Menu */}
      <AnimatePresence>
        {isOpen && (
          <>
            <div 
                className="fixed inset-0 z-40 bg-transparent" 
                onClick={() => setIsOpen(false)} 
            />
            <motion.div
              initial={{ opacity: 0, y: -10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -10, scale: 0.95 }}
              transition={{ duration: 0.2 }}
              className={cn(
                "absolute right-0 top-14 w-64 z-50 rounded-2xl border backdrop-blur-xl shadow-2xl p-2",
                isNight ? "bg-[#161b22]/90 border-rose-500/30 shadow-rose-900/10" : "bg-white/80 border-white/50 shadow-2xl"
              )}
            >
              <div className={cn("px-3 py-2 text-[10px] font-black uppercase tracking-widest", isNight ? "text-slate-500" : "text-slate-400")}>
                Select AI Model
              </div>
              
              <div className="space-y-1">
                {CHARACTERS.map((char) => (
                  <button
                    key={char.id}
                    onClick={() => {
                        setActiveCharacter(char.id)
                        setIsOpen(false)
                    }}
                    className={cn(
                      "group relative w-full flex items-center gap-3 p-2 rounded-xl transition-all border",
                      activeCharacterId === char.id
                        ? isNight
                             ? "bg-rose-900/40 border-rose-500/30"
                             : (char.id === 'arona' ? "bg-blue-50 border-blue-200" : "bg-rose-50 border-rose-200")
                        : "bg-transparent border-transparent hover:bg-slate-50/10 hover:border-white/10"
                    )}
                  >
                    <div className={cn(
                      "w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold text-white shadow-sm transition-transform group-hover:scale-110",
                       char.id === 'arona' ? "bg-blue-400" : "bg-rose-400"
                    )}>
                      {char.name[0]}
                    </div>
                    
                    <div className="flex-1 text-left">
                      <div className={cn(
                        "text-sm font-bold",
                        isNight 
                            ? (activeCharacterId === char.id ? "text-white" : "text-slate-400 group-hover:text-slate-200")
                            : (activeCharacterId === char.id ? "text-slate-900" : "text-slate-600")
                      )}>
                        {char.name}
                      </div>
                      <div className="text-[10px] text-slate-400 font-medium">
                        {char.role}
                      </div>
                    </div>

                    {activeCharacterId === char.id && (
                        <div className={cn(
                            "p-1 rounded-full",
                            isNight 
                                ? "text-rose-400 bg-rose-900/50"
                                : (char.id === 'arona' ? "text-blue-500 bg-blue-100" : "text-rose-500 bg-rose-100")
                        )}>
                            <Check className="w-3 h-3" strokeWidth={4} />
                        </div>
                    )}
                  </button>
                ))}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  )
}
