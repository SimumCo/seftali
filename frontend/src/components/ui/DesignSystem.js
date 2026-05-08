// Dağıtım Yönetim Sistemi - Ortak Layout ve Bileşenler
// Tüm dashboard'lar için tutarlı yapı sağlar

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Search, LogOut, Bell, ChevronRight, Home, CheckCheck, X } from 'lucide-react';
import { notificationsAPI } from '../../services/api';

// ============================================
// RENK PALETİ VE GRADIENTLAR
// ============================================
export const colors = {
  primary: 'orange',
  primaryLight: 'orange-50',
  primaryMedium: 'orange-500',
  primaryDark: 'orange-600',
  secondary: 'slate',
  success: 'emerald',
  warning: 'amber',
  danger: 'red',
  info: 'sky',
};

export const gradients = {
  blue: 'bg-gradient-to-br from-blue-500 to-blue-600',
  green: 'bg-gradient-to-br from-emerald-500 to-emerald-600',
  amber: 'bg-gradient-to-br from-amber-500 to-amber-600',
  orange: 'bg-gradient-to-br from-orange-500 to-orange-600',
  red: 'bg-gradient-to-br from-red-500 to-red-600',
  sky: 'bg-gradient-to-br from-sky-500 to-sky-600',
  purple: 'bg-gradient-to-br from-purple-500 to-purple-600',
};

// ============================================
// ANA LAYOUT BİLEŞENİ
// Tüm dashboard'lar için ortak wrapper
// ============================================
export const DashboardLayout = ({ 
  children, 
  sidebarItems, 
  activeTab, 
  setActiveTab, 
  onLogout, 
  user,
  title = 'Panel',
  headerContent,
}) => {
  const userInitial = user?.full_name?.charAt(0) || 'U';
  const userName = user?.full_name || 'Kullanici';

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Sidebar */}
      <Sidebar
        items={sidebarItems}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onLogout={onLogout}
        userInitial={userInitial}
        userName={userName}
        title={title}
      />

      {/* Main Content */}
      <main className="flex-1 ml-56">
        {/* Header */}
        <Header 
          userName={userName}
          userInitial={userInitial}
        >
          {headerContent}
        </Header>

        {/* Page Content */}
        <div className="p-6">
          {children}
        </div>
      </main>
    </div>
  );
};

// ============================================
// SIDEBAR BİLEŞENİ
// ============================================
export const Sidebar = ({ 
  items, 
  activeTab, 
  setActiveTab, 
  onLogout, 
  userInitial, 
  userName,
  title = 'Panel'
}) => (
  <aside className="w-56 bg-white border-r border-slate-200 flex flex-col fixed h-full z-30" data-testid="sidebar">
    {/* Logo */}
    <div className="p-4 border-b border-slate-200">
      <div className="flex items-center gap-2">
        <span className="text-2xl">🍑</span>
        <div>
          <span className="text-xl font-bold text-slate-900">Dagitim</span>
          <p className="text-[10px] text-slate-500">{title}</p>
        </div>
      </div>
    </div>

    {/* Navigation */}
    <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
      {items.map(item => (
        <NavItem 
          key={item.id}
          item={item}
          isActive={activeTab === item.id}
          onClick={() => setActiveTab(item.id)}
        />
      ))}
    </nav>

    {/* User & Logout */}
    <div className="p-3 border-t border-slate-200">
      <UserInfo userInitial={userInitial} userName={userName} />
      <LogoutButton onClick={onLogout} />
    </div>
  </aside>
);

// Navigation Item
const NavItem = ({ item, isActive, onClick }) => {
  const Icon = item.icon;
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all relative ${
        isActive 
          ? 'bg-orange-500 text-white shadow-md' 
          : 'text-slate-600 hover:bg-slate-100'
      }`}
      data-testid={`nav-${item.id}`}
    >
      <Icon className="w-5 h-5" />
      {item.label}
      {item.badge > 0 && (
        <span className={`absolute right-2 w-5 h-5 rounded-full text-xs flex items-center justify-center font-bold ${
          isActive ? 'bg-white text-orange-500' : 'bg-red-500 text-white'
        }`}>
          {item.badge}
        </span>
      )}
    </button>
  );
};

// User Info
const UserInfo = ({ userInitial, userName }) => (
  <div className="flex items-center gap-3 px-3 py-2 mb-2" data-testid="sidebar-user-info">
    <div className="w-9 h-9 bg-orange-500 rounded-full flex items-center justify-center text-white font-bold">
      {userInitial}
    </div>
    <span className="text-sm font-medium text-slate-700 truncate">{userName}</span>
  </div>
);

// Logout Button
const LogoutButton = ({ onClick }) => (
  <button 
    onClick={onClick}
    className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-slate-600 hover:bg-red-50 hover:text-red-600 transition-all"
    data-testid="logout-btn"
  >
    <LogOut className="w-5 h-5" />
    Cikis Yap
  </button>
);

// ============================================
// HEADER BİLEŞENİ
// ============================================
export const Header = ({ 
  children, 
  userName, 
  userInitial, 
  searchPlaceholder = "Ara..."
}) => (
  <header className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between sticky top-0 z-20" data-testid="dashboard-header">
    <div className="relative flex-1 max-w-md">
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
      <input 
        type="text" 
        placeholder={searchPlaceholder}
        className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
        data-testid="dashboard-header-search-input"
      />
    </div>
    {children}
    <div className="flex items-center gap-4">
      <NotificationBell />
      <UserAvatar userInitial={userInitial} userName={userName} />
    </div>
  </header>
);

// Notification Bell — canlı sayaç + dropdown panel
const NotificationBell = () => {
  const [open, setOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifications, setNotifications] = useState([]);
  const [loadingList, setLoadingList] = useState(false);
  const containerRef = useRef(null);

  const fetchUnreadCount = useCallback(async () => {
    try {
      const res = await notificationsAPI.getUnreadCount();
      setUnreadCount(res.data?.count ?? 0);
    } catch (err) {
      console.debug('[NotificationBell] unread-count fetch failed:', err?.message);
    }
  }, []);

  const fetchNotifications = useCallback(async () => {
    setLoadingList(true);
    try {
      const res = await notificationsAPI.getAll({ limit: 30 });
      setNotifications(res.data?.data || []);
    } catch (err) {
      console.warn('[NotificationBell] notification list fetch failed:', err?.message);
    } finally {
      setLoadingList(false);
    }
  }, []);

  useEffect(() => {
    fetchUnreadCount();
    const interval = setInterval(fetchUnreadCount, 30000);
    return () => clearInterval(interval);
  }, [fetchUnreadCount]);

  useEffect(() => {
    if (!open) return;
    fetchNotifications();
  }, [open, fetchNotifications]);

  useEffect(() => {
    if (!open) return;
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [open]);

  const handleMarkRead = async (id) => {
    try {
      await notificationsAPI.markAsRead(id);
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (err) {
      console.warn('[NotificationBell] mark-read failed:', err?.message);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await notificationsAPI.markAllAsRead();
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (err) {
      console.warn('[NotificationBell] mark-all-read failed:', err?.message);
    }
  };

  const formatTime = (isoStr) => {
    if (!isoStr) return '';
    const d = new Date(isoStr);
    const now = new Date();
    const diffMs = now - d;
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return 'Az önce';
    if (diffMin < 60) return `${diffMin} dk önce`;
    const diffH = Math.floor(diffMin / 60);
    if (diffH < 24) return `${diffH} sa önce`;
    const diffD = Math.floor(diffH / 24);
    return `${diffD} gün önce`;
  };

  const typeColors = {
    order_created: 'bg-sky-100 text-sky-700',
    order_status: 'bg-emerald-100 text-emerald-700',
    campaign: 'bg-amber-100 text-amber-700',
    system: 'bg-slate-100 text-slate-600',
    fault_response: 'bg-red-100 text-red-700',
  };

  return (
    <div className="relative" ref={containerRef} data-testid="dashboard-notification-bell">
      {unreadCount > 0 && (
        <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full text-[10px] text-white flex items-center justify-center font-bold z-10 pointer-events-none">
          {unreadCount > 99 ? '99+' : unreadCount}
        </span>
      )}
      <button
        onClick={() => setOpen(v => !v)}
        className="p-2 hover:bg-slate-100 rounded-full relative"
        data-testid="dashboard-notification-button"
        aria-label="Bildirimler"
      >
        <Bell className="w-5 h-5 text-slate-600" />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 bg-white border border-slate-200 rounded-2xl shadow-xl z-50 flex flex-col max-h-[480px]" data-testid="notification-panel">
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
            <h3 className="text-sm font-semibold text-slate-800">
              Bildirimler
              {unreadCount > 0 && (
                <span className="ml-2 bg-red-500 text-white text-[10px] font-bold rounded-full px-1.5 py-0.5">
                  {unreadCount}
                </span>
              )}
            </h3>
            <div className="flex items-center gap-1">
              {unreadCount > 0 && (
                <button
                  onClick={handleMarkAllRead}
                  className="flex items-center gap-1 text-xs text-slate-500 hover:text-orange-600 px-2 py-1 rounded-lg hover:bg-orange-50 transition-colors"
                  data-testid="notification-mark-all-read"
                  title="Tümünü okundu işaretle"
                >
                  <CheckCheck className="w-3.5 h-3.5" />
                  Tümü
                </button>
              )}
              <button
                onClick={() => setOpen(false)}
                className="p-1 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-600"
                data-testid="notification-panel-close"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto">
            {loadingList ? (
              <div className="flex justify-center py-8">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-orange-500" />
              </div>
            ) : notifications.length === 0 ? (
              <div className="text-center py-10">
                <Bell className="w-8 h-8 text-slate-200 mx-auto mb-2" />
                <p className="text-sm text-slate-400">Bildirim yok</p>
              </div>
            ) : (
              <ul>
                {notifications.map(n => (
                  <li
                    key={n.id}
                    className={`px-4 py-3 border-b border-slate-50 last:border-b-0 flex gap-3 cursor-pointer transition-colors ${n.is_read ? 'hover:bg-slate-50' : 'bg-orange-50 hover:bg-orange-100'}`}
                    onClick={() => !n.is_read && handleMarkRead(n.id)}
                    data-testid={`notification-item-${n.id}`}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <p className={`text-xs font-semibold truncate ${n.is_read ? 'text-slate-600' : 'text-slate-900'}`}>
                          {n.title}
                        </p>
                        {!n.is_read && (
                          <span className="flex-shrink-0 w-2 h-2 bg-orange-500 rounded-full mt-1" />
                        )}
                      </div>
                      <p className={`text-xs mt-0.5 line-clamp-2 ${n.is_read ? 'text-slate-400' : 'text-slate-600'}`}>
                        {n.message}
                      </p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${typeColors[n.type] || 'bg-slate-100 text-slate-500'}`}>
                          {n.type?.replace(/_/g, ' ')}
                        </span>
                        <span className="text-[10px] text-slate-400">{formatTime(n.created_at)}</span>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// User Avatar
const UserAvatar = ({ userInitial, userName }) => (
  <div className="flex items-center gap-2" data-testid="dashboard-user-avatar">
    <div className="w-9 h-9 bg-orange-500 rounded-full flex items-center justify-center text-white font-bold">
      {userInitial}
    </div>
    <span className="text-sm font-medium text-slate-700">{userName}</span>
  </div>
);

// ============================================
// SAYFA BİLEŞENLERİ
// ============================================

// Page Header
export const PageHeader = ({ title, subtitle, rightContent }) => (
  <div className="flex items-start justify-between mb-6">
    <div>
      <h1 className="text-2xl font-bold text-slate-900">{title}</h1>
      {subtitle && <p className="text-sm text-slate-500 mt-0.5">{subtitle}</p>}
    </div>
    {rightContent}
  </div>
);

// Stat Card
export const StatCard = ({ 
  title, 
  value, 
  subtitle, 
  icon: Icon, 
  gradient = gradients.blue, 
  onClick 
}) => (
  <button 
    onClick={onClick}
    className={`${gradient} rounded-2xl p-4 text-white text-left w-full hover:opacity-95 transition-opacity`}
  >
    {Icon && (
      <div className="flex items-center gap-2 mb-1">
        <Icon className="w-4 h-4 opacity-80" />
        <p className="text-xs font-medium opacity-80">{title}</p>
      </div>
    )}
    {!Icon && <p className="text-xs font-medium opacity-80">{title}</p>}
    <p className="text-2xl font-bold mt-1">{value}</p>
    {subtitle && <p className="text-xs opacity-70 mt-1">{subtitle}</p>}
  </button>
);

// Info Card (Container)
export const InfoCard = ({ title, children, className = '' }) => (
  <div className={`bg-white border border-slate-200 rounded-2xl p-4 ${className}`}>
    {title && <h3 className="text-sm font-semibold text-slate-700 mb-3">{title}</h3>}
    {children}
  </div>
);

// Empty State
export const EmptyState = ({ icon: Icon, title, subtitle }) => (
  <div className="text-center py-12 bg-white rounded-2xl border border-slate-200">
    {Icon && <Icon className="w-12 h-12 text-slate-300 mx-auto mb-3" />}
    <p className="text-slate-500 font-medium">{title}</p>
    {subtitle && <p className="text-sm text-slate-400 mt-1">{subtitle}</p>}
  </div>
);

// Loading Spinner
export const Loading = ({ size = 'md' }) => {
  const sizes = { sm: 'h-6 w-6', md: 'h-10 w-10', lg: 'h-12 w-12' };
  return (
    <div className="flex justify-center py-12">
      <div className={`animate-spin rounded-full ${sizes[size]} border-b-2 border-orange-500`} />
    </div>
  );
};

// Full Page Loading
export const FullPageLoading = () => (
  <div className="min-h-screen bg-slate-50 flex items-center justify-center">
    <Loading size="md" />
  </div>
);

// ============================================
// FORM BİLEŞENLERİ
// ============================================

// Button
export const Button = ({ 
  children, 
  variant = 'primary', 
  size = 'md', 
  icon: Icon, 
  onClick, 
  disabled,
  className = '',
  type = 'button'
}) => {
  const variants = {
    primary: 'bg-orange-500 text-white hover:bg-orange-600',
    secondary: 'bg-slate-100 text-slate-700 hover:bg-slate-200',
    success: 'bg-emerald-500 text-white hover:bg-emerald-600',
    danger: 'bg-red-500 text-white hover:bg-red-600',
    outline: 'border border-slate-200 text-slate-600 hover:bg-slate-50',
  };
  
  const sizes = {
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-2.5 text-sm',
    lg: 'px-6 py-3 text-base',
  };

  return (
    <button 
      type={type}
      onClick={onClick} 
      disabled={disabled}
      className={`flex items-center justify-center gap-2 rounded-xl font-medium transition-all disabled:opacity-50 ${variants[variant]} ${sizes[size]} ${className}`}
    >
      {Icon && <Icon className="w-4 h-4" />}
      {children}
    </button>
  );
};

// Badge
export const Badge = ({ children, variant = 'default' }) => {
  const variants = {
    default: 'bg-slate-100 text-slate-600',
    success: 'bg-green-50 text-green-700',
    warning: 'bg-amber-50 text-amber-700',
    danger: 'bg-red-50 text-red-700',
    info: 'bg-sky-50 text-sky-700',
  };

  return (
    <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${variants[variant]}`}>
      {children}
    </span>
  );
};

// List Item
export const ListItem = ({ title, subtitle, rightContent, onClick, badge, className = '' }) => (
  <button 
    onClick={onClick}
    className={`w-full bg-white border border-slate-200 rounded-2xl p-4 text-left hover:shadow-md transition-all ${className}`}
  >
    <div className="flex items-start justify-between">
      <div className="flex-1 min-w-0">
        <h3 className="font-bold text-slate-900 truncate">{title}</h3>
        {subtitle && <p className="text-sm text-slate-500 mt-0.5">{subtitle}</p>}
      </div>
      <div className="flex items-center gap-2 ml-3">
        {badge && <Badge>{badge}</Badge>}
        {rightContent}
        <ChevronRight className="w-4 h-4 text-slate-400" />
      </div>
    </div>
  </button>
);

// Quick Action Button
export const QuickAction = ({ icon: Icon, label, onClick, color = 'orange', badge }) => {
  const colors = {
    orange: 'bg-orange-50 hover:bg-orange-100 text-orange-600',
    emerald: 'bg-emerald-50 hover:bg-emerald-100 text-emerald-600',
    sky: 'bg-sky-50 hover:bg-sky-100 text-sky-600',
    amber: 'bg-amber-50 hover:bg-amber-100 text-amber-600',
  };

  return (
    <button 
      onClick={onClick}
      className={`w-full flex items-center justify-between p-3 ${colors[color]} rounded-xl transition-colors`}
    >
      <div className="flex items-center gap-3">
        <Icon className="w-5 h-5" />
        <span className="text-sm font-medium text-slate-800">{label}</span>
      </div>
      {badge > 0 && (
        <span className="bg-red-500 text-white text-xs w-5 h-5 rounded-full flex items-center justify-center font-bold">
          {badge}
        </span>
      )}
      <ChevronRight className="w-4 h-4 text-slate-400" />
    </button>
  );
};

// ============================================
// MOBİL BİLEŞENLERİ
// ============================================

// Mobile Header
export const MobileHeader = ({ onLogout }) => (
  <header className="lg:hidden bg-white border-b border-slate-200 px-4 py-3 flex items-center justify-between sticky top-0 z-20">
    <div className="flex items-center gap-2">
      <span className="text-xl">🍑</span>
      <span className="text-lg font-bold text-slate-900">Dagitim</span>
    </div>
    <button onClick={onLogout} className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-red-600 transition-colors">
      <LogOut className="w-4 h-4" />
      Cikis
    </button>
  </header>
);

// Mobile Bottom Navigation
export const BottomNav = ({ items, activeTab, setActiveTab }) => (
  <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-slate-200 z-20 lg:hidden" data-testid="bottom-nav">
    <div className="max-w-lg mx-auto flex">
      {items.map(item => {
        const Icon = item.icon;
        const isActive = activeTab === item.id;
        return (
          <button 
            key={item.id} 
            onClick={() => setActiveTab(item.id)}
            className={`flex-1 flex flex-col items-center py-2 relative transition-colors ${
              isActive ? 'text-orange-500' : 'text-slate-400 hover:text-slate-600'
            }`}
            data-testid={`nav-${item.id}`}
          >
            <Icon className="w-5 h-5" />
            <span className="text-[10px] mt-0.5 font-medium">{item.label}</span>
            {item.badge > 0 && (
              <span className="absolute top-1 right-1/4 bg-red-500 text-white text-[9px] w-4 h-4 rounded-full flex items-center justify-center font-bold">
                {item.badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  </nav>
);

// ============================================
// BACKWARD COMPATIBILITY (eski isimlerle export)
// ============================================
export const SeftaliSidebar = Sidebar;
export const SeftaliHeader = Header;
export const SeftaliPageHeader = PageHeader;
export const SeftaliStatCard = StatCard;
export const SeftaliInfoCard = InfoCard;
export const SeftaliButton = Button;
export const SeftaliEmptyState = EmptyState;
export const SeftaliLoading = Loading;
export const SeftaliBadge = Badge;
export const SeftaliBottomNav = BottomNav;
export const SeftaliListItem = ListItem;
export const AppSidebar = Sidebar;

export default {
  DashboardLayout,
  Sidebar,
  Header,
  PageHeader,
  StatCard,
  InfoCard,
  EmptyState,
  Loading,
  FullPageLoading,
  Button,
  Badge,
  ListItem,
  QuickAction,
  MobileHeader,
  BottomNav,
  gradients,
  colors,
};
