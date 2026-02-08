import React, { useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CHARACTERS, CharacterId } from '@/types/character'
import { useUIStore } from '@/store/ui-store'
import { cn } from '@/lib/utils'
import { Check } from 'lucide-react'
import { useTheme } from '@/components/providers/theme-provider'
import { getCycleConfig } from '@/lib/cycle-config'
import Image from 'next/image'

const CHARACTER_ICONS: Record<string, string> = {
  arona: '/images/arona_icon.png',
  plana: '/images/plana.icon.png',
}

const CHARACTER_THEME: Record<string, 'light' | 'dark'> = {
  arona: 'light',
  plana: 'dark',
}

export function CharacterSelector() {
  const activeCharacterId = useUIStore((state) => state.activeCharacterId)
  const setActiveCharacter = useUIStore((state) => state.setActiveCharacter)
  const [isOpen, setIsOpen] = React.useState(false)
  
  const { theme, setThemeManual, isAutoMode } = useTheme()
  const config = getCycleConfig(theme)
  const initialSyncDone = React.useRef(false)

  // On first mount, always sync character to match the current theme (whether auto or manual-restored)
  useEffect(() => {
    if (!initialSyncDone.current) {
      initialSyncDone.current = true
      if (activeCharacterId !== config.characterId) {
        setActiveCharacter(config.characterId as CharacterId)
      }
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // After initial sync, only auto-cycle when in auto mode
  useEffect(() => {
    if (initialSyncDone.current && isAutoMode && activeCharacterId !== config.characterId) {
        setActiveCharacter(config.characterId as CharacterId)
    }
  }, [theme, config.characterId, setActiveCharacter, activeCharacterId, isAutoMode])

  // Always use the store's active character for display, which is now synced
  const activeChar = CHARACTERS.find(c => c.id === activeCharacterId) || CHARACTERS[0]

  return (
    <div className="relative z-50">
      {/* Trigger Button */}
      <motion.button
        onClick={() => setIsOpen(!isOpen)}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        className="flex items-center gap-3 pl-2 pr-4 py-2 rounded-full border transition-all duration-300 backdrop-blur-md shadow-sm bg-[var(--char-trigger-bg)] border-[var(--char-trigger-border)] text-[var(--char-trigger-text)] hover:border-[var(--char-trigger-hover-border)] hover:bg-[var(--char-trigger-hover-bg)]"
      >
        <div className="w-8 h-8 rounded-full flex items-center justify-center overflow-hidden shadow-inner bg-[var(--char-avatar-bg)]">
          <Image
            src={CHARACTER_ICONS[activeChar.id] || CHARACTER_ICONS.arona}
            alt={activeChar.name}
            width={28}
            height={28}
            className="object-contain"
          />
        </div>
        <div className="text-left hidden sm:block">
          <div className="text-xs font-bold uppercase tracking-wider opacity-70 text-[var(--char-label-text)]">Assistant</div>
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
              className="absolute right-0 top-14 w-64 z-50 rounded-2xl border backdrop-blur-xl shadow-2xl p-2 bg-[var(--char-dropdown-bg)] border-[var(--char-dropdown-border)]"
            >
              <div className="px-3 py-2 text-[10px] font-black uppercase tracking-widest text-[var(--char-dropdown-heading)]">
                Select AI Model
              </div>
              
              <div className="space-y-1">
                {CHARACTERS.map((char) => (
                  <button
                    key={char.id}
                    onClick={() => {
                        setActiveCharacter(char.id)
                        if (CHARACTER_THEME[char.id]) {
                          setThemeManual(CHARACTER_THEME[char.id])
                        }
                        setIsOpen(false)
                    }}
                    className={cn(
                      "group relative w-full flex items-center gap-3 p-2 rounded-xl transition-all border",
                      activeCharacterId === char.id
                        ? "bg-[var(--char-item-active-bg)] border-[var(--char-item-active-border)]"
                        : "bg-transparent border-transparent hover:bg-slate-50/10 hover:border-white/10"
                    )}
                  >
                    <div className={cn(
                      "w-10 h-10 rounded-full flex items-center justify-center overflow-hidden shadow-sm transition-transform group-hover:scale-110",
                       char.id === 'arona' ? "bg-blue-400" : "bg-rose-400"
                    )}>
                      <Image
                        src={CHARACTER_ICONS[char.id] || CHARACTER_ICONS.arona}
                        alt={char.name}
                        width={32}
                        height={32}
                        className="object-contain"
                      />
                    </div>
                    
                    <div className="flex-1 text-left">
                      <div className={cn(
                        "text-sm font-bold",
                        activeCharacterId === char.id
                            ? "text-[var(--char-item-active-text)]"
                            : "text-[var(--char-item-text)] group-hover:text-foreground"
                      )}>
                        {char.name}
                      </div>
                      <div className="text-[10px] text-slate-400 font-medium">
                        {char.role}
                      </div>
                    </div>

                    {activeCharacterId === char.id && (
                        <div className="p-1 rounded-full text-[var(--char-check-text)] bg-[var(--char-check-bg)]">
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
