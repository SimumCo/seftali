# Design Guidelines: Production & Distribution Network Management System

## Design Approach
**System Selected:** Carbon Design System (IBM)
**Rationale:** Optimized for data-heavy enterprise applications with complex workflows, extensive table views, and multi-role user interfaces. Carbon excels at information architecture for production and logistics operations.

## Core Design Principles

### 1. Typography
- **Primary Font:** IBM Plex Sans (via Google Fonts CDN)
- **Headers:** 
  - Page titles: text-2xl font-semibold
  - Section headers: text-lg font-medium
  - Card titles: text-base font-medium
- **Body Text:** text-sm for dense information displays
- **Data Tables:** text-sm font-mono for numeric values (consistent alignment)

### 2. Layout System
**Spacing Units:** Tailwind primitives of 2, 4, 6, 8 (p-4, gap-6, m-8)
- Component padding: p-4 or p-6
- Section spacing: space-y-6 or space-y-8
- Grid gaps: gap-4 for tight layouts, gap-6 for card grids
- Page margins: Container with max-w-7xl mx-auto px-4

**Grid System:**
- Dashboard: 3-column grid (lg:grid-cols-3) for KPI cards
- Main content: 2-column split (2/3 main content, 1/3 sidebar)
- Data tables: Full-width with horizontal scroll on mobile
- Forms: Single column with max-w-2xl for readability

### 3. Component Library

**Navigation:**
- Sidebar navigation (fixed left, 240px wide on desktop)
- Collapsible sections for Production, Distribution, Inventory, Reports
- Top bar with user profile, notifications, quick actions
- Breadcrumbs for deep navigation paths

**Dashboard Components:**
- KPI Cards: Metric value (large), label, trend indicator (↑↓), sparkline chart
- Status Cards: Color-coded borders (blue=in-progress, green=completed, amber=pending)
- Quick Action Buttons: Prominent CTAs for "New Order", "Create Shipment"

**Data Display:**
- Tables: Sortable headers, row selection checkboxes, pagination
- Status Badges: Pill-shaped with semantic colors (production/transit/delivered)
- Timeline View: Vertical timeline for order/shipment tracking
- Maps: Distribution network visualization with location pins

**Forms:**
- Multi-step forms for complex workflows (Order Creation, Shipment Planning)
- Progress indicators showing current step (1/4, 2/4, etc.)
- Inline validation with clear error states
- Action buttons: Primary (submit), Secondary (save draft), Tertiary (cancel)

**Overlays:**
- Modal dialogs for confirmations and quick edits (max-w-2xl)
- Slide-over panels from right for detailed views (w-96)
- Toast notifications for success/error feedback (top-right position)

### 4. Page Structures

**Dashboard:**
- Top summary row: 4 KPI cards (Today's Production, Active Shipments, Pending Orders, Inventory Alerts)
- Chart row: Production trends (line chart), Distribution map
- Recent activity table below

**Production View:**
- Filter bar with date range, facility, status filters
- Production schedule table with expandable rows
- Action buttons per row: Edit, View Details, Mark Complete

**Distribution View:**
- Map on left (60% width), shipment list on right (40%)
- Shipment cards with status, ETA, driver info
- Route optimization suggestions panel

**Inventory Management:**
- Stock levels table with low-stock highlighting
- Warehouse selector dropdown
- Quick reorder buttons per item

### 5. Responsive Behavior
- Desktop (lg): Full sidebar + 3-column layouts
- Tablet (md): Collapsible sidebar + 2-column layouts
- Mobile: Hidden sidebar (hamburger menu) + single column stacked

### 6. Iconography
**Icon Library:** Heroicons (outline style via CDN)
- Navigation: truck, cube, chart-bar, document-report, cog
- Actions: plus-circle, pencil, trash, download, upload
- Status: check-circle, exclamation-circle, clock, x-circle

### 7. Interactive States
- Buttons: Solid fill with subtle shadow, no color shift on hover (brightness change only)
- Tables: Row hover with subtle background change (bg-gray-50)
- Cards: Subtle shadow on hover (shadow-md)
- No elaborate animations - focus on instant feedback

## Images
**No hero images required** - This is a functional dashboard application, not a marketing site. Use data visualizations, charts, and maps as primary visual elements instead.