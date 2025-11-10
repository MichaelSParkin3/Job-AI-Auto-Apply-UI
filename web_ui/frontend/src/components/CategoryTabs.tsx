import type { SettingsCategory } from '@/lib/types'

interface CategoryTabsProps {
  categories: SettingsCategory[]
  activeCategory: string
  onCategoryChange: (categoryId: string) => void
  errorCounts?: Record<string, number>
}

const categoryIcons: Record<string, string> = {
  llm: '🧠',
  browser: '🌐',
  general: '⚙️',
  network: '🔗',
  diagnostics: '🔍',
  advanced: '🚀',
}

export function CategoryTabs({
  categories,
  activeCategory,
  onCategoryChange,
  errorCounts = {},
}: CategoryTabsProps) {
  if (categories.length === 0) {
    return null
  }

  return (
    <div className="border-b border-gray-200">
      <nav className="flex gap-1 overflow-x-auto" aria-label="Settings categories">
        {categories.map((category) => {
          const icon = categoryIcons[category.id] || '📋'
          const isActive = activeCategory === category.id
          const errorCount = errorCounts[category.id] || 0
          const hasErrors = errorCount > 0

          return (
            <button
              key={category.id}
              onClick={() => onCategoryChange(category.id)}
              className={`px-4 py-3 text-sm font-medium whitespace-nowrap border-b-2 transition-colors relative ${
                isActive
                  ? 'border-blue-500 text-blue-600'
                  : hasErrors
                    ? 'border-red-300 text-red-600 hover:border-red-400 hover:text-red-700'
                    : 'border-transparent text-gray-600 hover:border-gray-300 hover:text-gray-900'
              }`}
              aria-current={isActive ? 'page' : undefined}
              title={category.description + (hasErrors ? ` - ${errorCount} error(s)` : '')}
            >
              <span className="mr-2">{icon}</span>
              {category.name}
              {hasErrors && (
                <span className="ml-2 inline-flex items-center justify-center w-5 h-5 text-xs font-bold text-white bg-red-500 rounded-full">
                  {errorCount}
                </span>
              )}
            </button>
          )
        })}
      </nav>
    </div>
  )
}
