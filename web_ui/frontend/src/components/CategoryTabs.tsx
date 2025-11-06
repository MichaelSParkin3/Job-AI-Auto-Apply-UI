import type { SettingsCategory } from '@/lib/types'

interface CategoryTabsProps {
  categories: SettingsCategory[]
  activeCategory: string
  onCategoryChange: (categoryId: string) => void
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

          return (
            <button
              key={category.id}
              onClick={() => onCategoryChange(category.id)}
              className={`px-4 py-3 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
                isActive
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-600 hover:border-gray-300 hover:text-gray-900'
              }`}
              aria-current={isActive ? 'page' : undefined}
              title={category.description}
            >
              <span className="mr-2">{icon}</span>
              {category.name}
            </button>
          )
        })}
      </nav>
    </div>
  )
}
