import React, { useState, useEffect } from 'react';
import { 
  Search, 
  Plus, 
  Star, 
  Clock, 
  MessageSquare,
  Music,
  Calendar,
  MapPin,
  Camera,
  Shield,
  Settings2,
  Download,
  Trash2
} from 'lucide-react';

const SkillsPanel = ({ skills = [], isLoading = false, error = null }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [filteredSkills, setFilteredSkills] = useState(Array.isArray(skills) ? skills : []);

  // Skill categories with icons
  const categories = [
    { id: 'all', label: 'All Skills', icon: Settings2 },
    { id: 'conversation', label: 'Conversation', icon: MessageSquare },
    { id: 'productivity', label: 'Productivity', icon: Calendar },
    { id: 'entertainment', label: 'Entertainment', icon: Music },
    { id: 'navigation', label: 'Navigation', icon: MapPin },
    { id: 'media', label: 'Media', icon: Camera },
    { id: 'system', label: 'System', icon: Shield }
  ];

  // Filter skills based on search and category
  useEffect(() => {
    let filtered = Array.isArray(skills) ? skills : [];

    if (selectedCategory !== 'all') {
      filtered = filtered.filter(skill => skill.category === selectedCategory);
    }

    if (searchTerm) {
      filtered = filtered.filter(skill => 
        skill.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        skill.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (skill.tags && skill.tags.some(tag => 
          tag.toLowerCase().includes(searchTerm.toLowerCase())
        ))
      );
    }

    setFilteredSkills(filtered);
  }, [skills, searchTerm, selectedCategory]);

  const handleToggleSkill = async (skillId, enabled) => {
    try {
      if (window.electronAPI) {
        await window.electronAPI.invoke('toggle-skill', { skillId, enabled });
      }
    } catch (error) {
      console.error('Failed to toggle skill:', error);
    }
  };

  const handleInstallSkill = async (skillId) => {
    try {
      if (window.electronAPI) {
        await window.electronAPI.invoke('install-skill', { skillId });
      }
    } catch (error) {
      console.error('Failed to install skill:', error);
    }
  };

  const handleUninstallSkill = async (skillId) => {
    try {
      if (window.electronAPI) {
        await window.electronAPI.invoke('uninstall-skill', { skillId });
      }
    } catch (error) {
      console.error('Failed to uninstall skill:', error);
    }
  };

  const SkillCard = ({ skill }) => {
    const IconComponent = categories.find(cat => cat.id === skill.category)?.icon || Settings2;
    
    return (
      <div className={`skill-card ${skill.enabled ? 'enabled' : 'disabled'}`}>
        <div className="skill-header">
          <div className="skill-icon">
            <IconComponent size={24} />
          </div>
          <div className="skill-info">
            <h4 className="skill-name">{skill.name}</h4>
            <span className="skill-version">v{skill.version}</span>
          </div>
          <div className="skill-actions">
            {skill.favorite && <Star size={16} className="text-warning" />}
            {skill.installed ? (
              <button
                className="btn btn-sm btn-outline-danger"
                onClick={() => handleUninstallSkill(skill.id)}
                title="Uninstall skill"
              >
                <Trash2 size={16} />
              </button>
            ) : (
              <button
                className="btn btn-sm btn-outline-primary"
                onClick={() => handleInstallSkill(skill.id)}
                title="Install skill"
              >
                <Download size={16} />
              </button>
            )}
          </div>
        </div>

        <p className="skill-description">{skill.description}</p>

        <div className="skill-meta">
          <div className="skill-tags">
            {skill.tags?.map(tag => (
              <span key={tag} className="skill-tag">{tag}</span>
            ))}
          </div>
          
          <div className="skill-stats">
            <span className="skill-stat">
              <Clock size={14} />
              {skill.lastUsed ? `Used ${skill.lastUsed}` : 'Never used'}
            </span>
          </div>
        </div>

        {skill.installed && (
          <div className="skill-controls">
            <label className="skill-toggle">
              <input
                type="checkbox"
                checked={skill.enabled}
                onChange={(e) => handleToggleSkill(skill.id, e.target.checked)}
              />
              <span className="toggle-slider"></span>
              <span className="toggle-label">
                {skill.enabled ? 'Enabled' : 'Disabled'}
              </span>
            </label>
          </div>
        )}
      </div>
    );
  };

  if (error) {
    return (
      <div className="skills-panel">
        <div className="error-state">
          <h3>Error Loading Skills</h3>
          <p>{error.message}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="skills-panel">
      <div className="skills-header">
        <h2>Skills Management</h2>
        <p>Manage your BUDDY's capabilities and skills</p>
      </div>

      {/* Search and Filter Controls */}
      <div className="skills-controls">
        <div className="search-bar">
          <Search size={20} className="search-icon" />
          <input
            type="text"
            placeholder="Search skills..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
        </div>

        <div className="category-filter">
          {categories.map(category => {
            const IconComponent = category.icon;
            return (
              <button
                key={category.id}
                className={`category-btn ${selectedCategory === category.id ? 'active' : ''}`}
                onClick={() => setSelectedCategory(category.id)}
              >
                <IconComponent size={18} />
                {category.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Skills Grid */}
      <div className="skills-content">
        {isLoading ? (
          <div className="loading-state">
            <div className="loading-spinner"></div>
            <p>Loading skills...</p>
          </div>
        ) : filteredSkills.length === 0 ? (
          <div className="empty-state">
            <Plus size={48} className="text-muted" />
            <h3>No Skills Found</h3>
            <p>
              {searchTerm || selectedCategory !== 'all' 
                ? 'Try adjusting your search or filter.'
                : 'No skills are currently available.'}
            </p>
          </div>
        ) : (
          <div className="skills-grid">
            {filteredSkills.map(skill => (
              <SkillCard key={skill.id} skill={skill} />
            ))}
          </div>
        )}
      </div>

      {/* Skills Summary */}
      <div className="skills-summary">
        <div className="summary-stat">
          <strong>{Array.isArray(skills) ? skills.filter(s => s.installed).length : 0}</strong>
          <span>Installed</span>
        </div>
        <div className="summary-stat">
          <strong>{Array.isArray(skills) ? skills.filter(s => s.enabled).length : 0}</strong>
          <span>Enabled</span>
        </div>
        <div className="summary-stat">
          <strong>{Array.isArray(skills) ? skills.filter(s => s.favorite).length : 0}</strong>
          <span>Favorites</span>
        </div>
      </div>
    </div>
  );
};

export default SkillsPanel;
