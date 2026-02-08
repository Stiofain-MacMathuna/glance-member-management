<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import axios from 'axios'

// --- STATE ---
const currentApp = ref('directory')
const loading = ref(true)
const searchQuery = ref('')
const sortBy = ref('last_name')
const showFilters = ref(false)
const showExportMenu = ref(false)
const legacyMode = ref(false)

// Filters state
const filters = ref({ country: '', institute: '', mo_status: '', status: '', group: '', phase: '' })

// TIMEOUT VARIABLE
let timeout = null

// Data
const members = ref([])
const papers = ref([])
const stats = ref(null)

// Pagination
const totalCount = ref(0)
const nextUrl = ref(null)
const prevUrl = ref(null)
const currentPage = ref(1)

// Auth
const isLoggedIn = ref(false)
const showLoginModal = ref(false)
const loginForm = ref({ username: '', password: '' })

// Modals
const selectedMember = ref(null)
const memberTab = ref('profile')
const selectedPaper = ref(null)
const isEditing = ref(false)
const editForm = ref({})

// Calendar & Shift Logic
const calendarDate = ref(new Date())
const showDayModal = ref(false)
const selectedDayData = ref({ date: '', shifts: [] })
const newShift = ref({ type: 'MORNING', location: 'P5 Control Room' })
const shiftError = ref('')

const totalPages = computed(() => Math.ceil(totalCount.value / 20))

// NOTIFICATION STATE
const notification = ref({ show: false, message: '', type: 'success' })

// --- HELPER: NOTIFICATIONS ---
const showNotification = (msg, type = 'success') => {
  notification.value = { show: true, message: msg, type: type }
  setTimeout(() => {
    notification.value.show = false
  }, 3000) // Disappears after 3 seconds
}

// --- MOCK AUDIT DATA ---
const getAuditLog = (member) => {
  return [
    { id: 1, date: '2025-02-07 14:30', user: 'Admin (You)', action: 'Updated M&O Status', detail: 'Changed to Qualified' },
    { id: 2, date: '2025-02-06 09:15', user: 'System', action: 'Shift Assigned', detail: 'Added Morning Shift (Feb 14)' },
    { id: 3, date: '2025-01-20 11:00', user: 'Import Bot', action: 'Profile Created', detail: 'Imported from Legacy Java DB' },
  ]
}

// --- CALENDAR LOGIC ---
const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

const calendarHeader = computed(() => {
  return `${monthNames[calendarDate.value.getMonth()]} ${calendarDate.value.getFullYear()}`
})

const calendarGrid = computed(() => {
  const year = calendarDate.value.getFullYear()
  const month = calendarDate.value.getMonth()
  const firstDay = new Date(year, month, 1).getDay()
  const startOffset = firstDay === 0 ? 6 : firstDay - 1
  const daysInMonth = new Date(year, month + 1, 0).getDate()

  const days = []
  for (let i = 0; i < startOffset; i++) days.push(null)
  for (let i = 1; i <= daysInMonth; i++) days.push(i)
  return days
})

const changeMonth = (delta) => {
  const newDate = new Date(calendarDate.value)
  newDate.setMonth(newDate.getMonth() + delta)
  calendarDate.value = newDate
}

const getShiftsForDay = (day) => {
  if (!day || !selectedMember.value.shifts) return []
  const year = calendarDate.value.getFullYear()
  const month = calendarDate.value.getMonth() + 1
  const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
  return selectedMember.value.shifts.filter(s => s.date === dateStr)
}

// --- SHIFT MANAGEMENT ---
const openDayManager = (day) => {
  if (!isLoggedIn.value) {
    alert("Please log in (Admin Access) to manage shifts.")
    return
  }
  if (!day) return

  const year = calendarDate.value.getFullYear()
  const month = calendarDate.value.getMonth() + 1
  const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`

  const memberShifts = selectedMember.value.shifts || []
  const existingShifts = memberShifts.filter(s => s.date === dateStr)

  selectedDayData.value = {
    date: dateStr,
    dayDisplay: `${day} ${monthNames[calendarDate.value.getMonth()]}`,
    shifts: existingShifts
  }

  newShift.value = { type: 'MORNING', location: 'P5 Control Room' }
  shiftError.value = ''
  showDayModal.value = true
}

const submitShift = async () => {
  try {
    const payload = {
      date: selectedDayData.value.date,
      type: newShift.value.type,
      location: newShift.value.location,
      member: selectedMember.value.id
    }

    const response = await axios.post('/api/shifts/', payload)

    if (!selectedMember.value.shifts) selectedMember.value.shifts = []

    selectedMember.value.shifts.push(response.data)
    selectedDayData.value.shifts.push(response.data)

    // Update Audit Log
    if (selectedMember.value.auditLogs) {
      selectedMember.value.auditLogs.unshift({
        id: Date.now(),
        date: new Date().toLocaleString(),
        user: 'Admin (You)',
        action: 'Shift Assigned',
        detail: `${newShift.value.type} - ${newShift.value.location} (${selectedDayData.value.date})`
      })
    }

    shiftError.value = ''
    showNotification("Shift successfully assigned", "success")
  } catch (err) {
    if (err.response && err.response.data.detail) {
       shiftError.value = err.response.data.detail
    } else {
       showNotification("Failed to add shift", "error")
    }
  }
}

const deleteShift = async (shiftId) => {
  if (!confirm("Remove this shift?")) return

  try {
    const shiftToRemove = selectedMember.value.shifts.find(s => s.id === shiftId)
    await axios.delete(`/api/shifts/${shiftId}/`)
    selectedMember.value.shifts = selectedMember.value.shifts.filter(s => s.id !== shiftId)
    selectedDayData.value.shifts = selectedDayData.value.shifts.filter(s => s.id !== shiftId)

    // Update Audit Log
    if (selectedMember.value.auditLogs && shiftToRemove) {
      selectedMember.value.auditLogs.unshift({
        id: Date.now(),
        date: new Date().toLocaleString(),
        user: 'Admin (You)',
        action: 'Shift Deleted',
        detail: `${shiftToRemove.type} (${shiftToRemove.date})`
      })
    }
    showNotification("Shift removed", "success")
  } catch (err) {
    showNotification("Failed to delete shift", "error")
  }
}

// --- AXIOS CONFIG ---
axios.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) config.headers['Authorization'] = `Bearer ${token}`
    return config
  },
  (error) => Promise.reject(error)
)

axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('access_token')
      isLoggedIn.value = false
      if (localStorage.getItem('access_token')) window.location.reload()
    }
    return Promise.reject(error)
  }
)

// --- FETCHING ---
const buildUrl = (endpoint, forExport = false) => {
  const baseUrl = `/api/${endpoint}/`
  const finalBase = forExport ? `${baseUrl}export/` : baseUrl

  const query = searchQuery.value ? `?search=${encodeURIComponent(searchQuery.value)}` : '?'

  let order = sortBy.value
  if (currentApp.value === 'directory' && ['creation_date', 'phase', 'group'].includes(order)) order = 'last_name'
  if (currentApp.value === 'analysis' && ['last_name', 'cern_id'].includes(order)) order = '-creation_date'

  let url = `${finalBase}${query}&ordering=${order}`

  if (currentApp.value === 'directory') {
    if (filters.value.country) url += `&institute__country=${encodeURIComponent(filters.value.country)}`
    if (filters.value.institute) url += `&institute__name__icontains=${encodeURIComponent(filters.value.institute)}`
    if (filters.value.mo_status) url += `&is_mo_qualified=${filters.value.mo_status}`
    if (filters.value.status) url += `&cern_status=${filters.value.status}`
  } else {
    if (filters.value.group) url += `&group=${filters.value.group}`
    if (filters.value.phase) url += `&phase=${filters.value.phase}`
  }
  return url
}

const fetchStats = async () => {
  loading.value = true
  try {
    const response = await axios.get('/api/stats/')
    stats.value = response.data
  } catch (err) { console.error(err) }
  loading.value = false
}

const fetchMembers = async (url = null) => {
  loading.value = true
  if (!url) { url = buildUrl('members'); currentPage.value = 1 }
  try {
    const response = await axios.get(url)
    members.value = response.data.results || response.data
    totalCount.value = response.data.count || members.value.length
    nextUrl.value = response.data.next; prevUrl.value = response.data.previous
  } catch (err) { console.error(err) }
  loading.value = false
}

const fetchPapers = async (url = null) => {
  loading.value = true
  if (!url) { url = buildUrl('analyses'); currentPage.value = 1 }
  try {
    const response = await axios.get(url)
    papers.value = response.data.results || response.data
    totalCount.value = response.data.count || papers.value.length
    nextUrl.value = response.data.next; prevUrl.value = response.data.previous
  } catch (err) { console.error(err) }
  loading.value = false
}

const loadData = () => {
  if (currentApp.value === 'dashboard') fetchStats()
  else if (currentApp.value === 'directory') fetchMembers()
  else fetchPapers()
}

watch(currentApp, (newApp) => {
  searchQuery.value = ''
  filters.value = { country: '', institute: '', mo_status: '', status: '', group: '', phase: '' }
  if (newApp === 'directory') sortBy.value = 'last_name'
  else if (newApp === 'analysis') sortBy.value = '-creation_date'
  loadData()
})
watch([sortBy, filters], () => loadData(), { deep: true })

const onSearchInput = () => {
  clearTimeout(timeout)
  timeout = setTimeout(() => { loadData() }, 300)
}

const loadPage = (url, direction) => {
  if (url) {
    if (currentApp.value === 'directory') fetchMembers(url); else fetchPapers(url)
    if (direction === 'next') currentPage.value++; if (direction === 'prev') currentPage.value--
  }
}

const triggerExport = (type) => {
  showExportMenu.value = false
  if (type === 'all') {
    const endpoint = currentApp.value === 'directory' ? 'members' : 'analyses'
    const exportUrl = buildUrl(endpoint, true)
    window.location.href = exportUrl
  } else {
    downloadCurrentPage()
  }
}

const downloadCurrentPage = () => {
  const data = currentApp.value === 'directory' ? members.value : papers.value
  if (!data || data.length === 0) return alert("No data to export")
  let csvContent = "data:text/csv;charset=utf-8,"
  if (currentApp.value === 'directory') {
    csvContent += "CERN_ID,Last_Name,First_Name,Institute,Country,Status,MO_Qualified\n"
    data.forEach(row => { csvContent += `${row.cern_id},"${row.last_name}","${row.first_name}","${row.institute_name}","${row.institute_country}",${row.cern_status},${row.is_mo_qualified}\n` })
  } else {
    csvContent += "RefCode,Experiment,Title,Phase,Status,AuthorCount\n"
    data.forEach(row => { csvContent += `${row.ref_code},${row.group},"${row.title}",${row.phase_name},${row.status_text},${row.author_count}\n` })
  }
  const encodedUri = encodeURI(csvContent)
  const link = document.createElement("a")
  link.setAttribute("href", encodedUri)
  link.setAttribute("download", `glance_page_${currentPage.value}.csv`)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

const login = async () => {
  try {
    const response = await axios.post('/api/token/', { username: loginForm.value.username, password: loginForm.value.password })
    localStorage.setItem('access_token', response.data.access)
    isLoggedIn.value = true; showLoginModal.value = false; loadData()
  } catch (err) { alert("Login failed! Ensure user 'cern' exists.") }
}
const logout = () => { localStorage.removeItem('access_token'); isLoggedIn.value = false; alert("Logged out.") }

// OPEN MEMBER
const openMember = (member) => {
  selectedMember.value = member
  member.auditLogs = getAuditLog(member)
  memberTab.value = 'profile'
  editForm.value = { ...member }
  isEditing.value = false
  calendarDate.value = new Date()
}

const openPaper = (paper) => { selectedPaper.value = paper }
const closeModals = () => { selectedMember.value = null; selectedPaper.value = null; isEditing.value = false }
const saveMember = async () => {
  if (!selectedMember.value) return
  try {
    // UPDATED: Relative URL for Docker/Nginx
    await axios.patch(`/api/members/${selectedMember.value.id}/`, editForm.value)
    Object.assign(selectedMember.value, editForm.value)
    if (selectedMember.value.auditLogs) {
      selectedMember.value.auditLogs.unshift({
         id: Date.now(), date: new Date().toLocaleString(), user: 'Admin (You)', action: 'Updated Profile', detail: 'Manual Edit'
      })
    }
    isEditing.value = false
    showNotification("Profile updated successfully", "success")
  } catch (err) { alert("Failed to save.") }
}

onMounted(() => {
  const token = localStorage.getItem('access_token'); if (token) isLoggedIn.value = true
  loadData()
})
</script>

<template>
  <div :class="['layout', { 'legacy-mode': legacyMode }]">

    <transition name="slide-fade">
      <div v-if="notification.show" :class="['notification-toast', notification.type]">
        <div class="toast-content">
          <svg v-if="notification.type === 'success'" class="toast-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
          <svg v-else class="toast-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
          <span>{{ notification.message }}</span>
        </div>
      </div>
    </transition>

    <aside class="sidebar">
      <div class="brand">
        <div class="logo-box">CMS</div>
        <h2>GLANCE</h2>
      </div>
      <div class="nav-section">
        <div class="nav-label">Main Navigation</div>
        <button @click="currentApp = 'dashboard'" :class="['nav-item', { active: currentApp === 'dashboard' }]">
          <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"></path></svg> Incubator Dashboard
        </button>
        <button @click="currentApp = 'directory'" :class="['nav-item', { active: currentApp === 'directory' }]">
          <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path></svg> Member Directory
        </button>
        <button @click="currentApp = 'analysis'" :class="['nav-item', { active: currentApp === 'analysis' }]">
          <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"></path></svg> Analysis Tracker
        </button>
      </div>
      <div class="legacy-toggle-box">
         <label class="toggle-switch-small">
           <input type="checkbox" v-model="legacyMode">
           <span class="slider-small"></span>
           <span class="label-small">Legacy Mode</span>
         </label>
      </div>
      <div class="auth-box">
        <div v-if="isLoggedIn" class="user-info">
          <div class="avatar-small">A</div>
          <div class="user-text"><strong>Administrator</strong><button @click="logout" class="link-logout">Sign Out</button></div>
        </div>
        <button v-else @click="showLoginModal = true" class="btn-login-side">Admin Access</button>
      </div>
    </aside>

    <main class="main-content">
      <header class="top-bar">
        <div class="left-controls" v-if="currentApp !== 'dashboard'">
          <div class="search-wrapper">
            <svg class="search-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
            <input v-model="searchQuery" @input="onSearchInput" type="text" :placeholder="currentApp === 'directory' ? 'Search members, institutes, IDs...' : 'Search papers...'" />
          </div>
          <button @click="showFilters = !showFilters" :class="['btn-filter', { active: showFilters }]">
            <svg class="icon-filter" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"></path></svg> Filters
          </button>
        </div>
        <div class="left-controls" v-else>
           <h2 class="page-title">Incubator Dashboard</h2>
        </div>
        <div class="controls-right" v-if="currentApp !== 'dashboard'">
           <div class="export-wrapper">
             <button @click="showExportMenu = !showExportMenu" class="btn-export">
               <svg class="icon-sm" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg> Export
             </button>
             <div v-if="showExportMenu" class="export-menu fade-in-down" @click.self="showExportMenu = false">
                <div class="menu-item" @click="triggerExport('page')"><span>Export Current Page</span><small>Visible rows only (CSV)</small></div>
                <div class="menu-item" @click="triggerExport('all')"><span>Export All Data</span><small>Full dataset (CSV)</small></div>
             </div>
           </div>
           <div class="header-divider"></div>
           <div class="sort-control">
             <span class="label">Sort by</span>
             <select v-model="sortBy" class="sort-select">
                <template v-if="currentApp === 'directory'">
                  <option value="last_name">Alphabetical</option>
                  <option value="cern_id">CERN ID</option>
                  <option value="institute__name">Institute</option>
                </template>
                <template v-else>
                  <option value="-creation_date">Newest</option>
                  <option value="phase">Phase</option>
                  <option value="group">Experiment</option>
                </template>
             </select>
           </div>
           <div class="header-divider"></div>
           <span class="count-badge">{{ totalCount }} Records</span>
        </div>
      </header>

      <div v-if="showFilters && currentApp !== 'dashboard'" class="filter-panel fade-in-down">
        <div class="filter-row">
          <template v-if="currentApp === 'directory'">
            <div class="filter-group">
                <label>Institute Name</label>
                <input v-model="filters.institute" placeholder="e.g. CERN, MIT..." class="filter-input"/>
            </div>
            <div class="filter-group">
                <label>Country</label>
                <select v-model="filters.country">
                    <option value="">All Countries</option>
                    <optgroup label="Member States">
                        <option value="Austria">Austria</option><option value="Belgium">Belgium</option><option value="Bulgaria">Bulgaria</option>
                        <option value="Czech Republic">Czech Republic</option><option value="Denmark">Denmark</option><option value="Estonia">Estonia</option>
                        <option value="Finland">Finland</option><option value="France">France</option><option value="Germany">Germany</option>
                        <option value="Greece">Greece</option><option value="Hungary">Hungary</option><option value="Israel">Israel</option>
                        <option value="Italy">Italy</option><option value="Netherlands">Netherlands</option><option value="Norway">Norway</option>
                        <option value="Poland">Poland</option><option value="Portugal">Portugal</option><option value="Romania">Romania</option>
                        <option value="Serbia">Serbia</option><option value="Slovakia">Slovakia</option><option value="Slovenia">Slovenia</option>
                        <option value="Spain">Spain</option><option value="Sweden">Sweden</option><option value="Switzerland">Switzerland</option>
                        <option value="United Kingdom">United Kingdom</option>
                    </optgroup>
                    <optgroup label="Partners & Associates">
                        <option value="USA">USA</option><option value="China">China</option><option value="Japan">Japan</option>
                        <option value="South Korea">South Korea</option><option value="India">India</option><option value="Brazil">Brazil</option>
                        <option value="Ireland">Ireland</option><option value="Türkiye">Türkiye</option><option value="Ukraine">Ukraine</option>
                        <option value="Pakistan">Pakistan</option><option value="Croatia">Croatia</option><option value="Cyprus">Cyprus</option>
                        <option value="Latvia">Latvia</option><option value="Lithuania">Lithuania</option>
                    </optgroup>
                </select>
            </div>
            <div class="filter-group"><label>M&O Qualification</label><select v-model="filters.mo_status"><option value="">All</option><option value="true">Qualified</option><option value="false">Not Qualified</option></select></div>
            <div class="filter-group"><label>Status</label><select v-model="filters.status"><option value="">All</option><option value="USER">User</option><option value="STAFF">Staff</option><option value="FELLOW">Fellow</option></select></div>
          </template>
          <template v-else>
            <div class="filter-group"><label>Experiment</label><select v-model="filters.group"><option value="">All</option><option value="ATLAS">ATLAS</option><option value="CMS">CMS</option><option value="ALICE">ALICE</option><option value="LHCb">LHCb</option></select></div>
            <div class="filter-group"><label>Phase</label><select v-model="filters.phase"><option value="">All</option><option value="0">Phase 0</option><option value="1">Phase 1</option><option value="2">Phase 2</option><option value="3">Published</option></select></div>
          </template>
          <button @click="filters = {country:'', institute: '', mo_status:'', status:'', group:'', phase:''}" class="btn-clear">Reset</button>
        </div>
      </div>

      <div v-if="currentApp === 'dashboard' && stats" class="app-view fade-in">

         <div class="kpi-grid">
            <div class="kpi-card">
               <div class="card-header-row">
                  <div class="kpi-label">Total Members</div>
                  <div class="tooltip-container" data-tooltip="Active personnel across all contract types (Staff, Users, Students).">ⓘ</div>
               </div>
               <div class="kpi-val">{{ stats.metrics.total_members }}</div>
               <div class="kpi-sub">Registered in DB</div>
            </div>
            <div class="kpi-card">
               <div class="card-header-row">
                  <div class="kpi-label">M&O Authors</div>
                  <div class="tooltip-container" data-tooltip="PhDs qualified for Maintenance & Operations (M&O) cost sharing.">ⓘ</div>
               </div>
               <div class="kpi-val text-success">{{ stats.metrics.mo_percent }}%</div>
               <div class="kpi-sub">{{ stats.metrics.mo_qualified_count }} Qualified PhDs</div>
            </div>
            <div class="kpi-card">
               <div class="card-header-row">
                  <div class="kpi-label">Analyses</div>
                  <div class="tooltip-container" data-tooltip="Total active and published analysis papers.">ⓘ</div>
               </div>
               <div class="kpi-val text-blue">{{ stats.metrics.total_papers }}</div>
               <div class="kpi-sub">Active & Published</div>
            </div>
            <div class="kpi-card">
               <div class="card-header-row">
                  <div class="kpi-label">Upcoming Shifts</div>
                  <div class="tooltip-container" data-tooltip="Shifts scheduled for the next 30 days.">ⓘ</div>
               </div>
               <div class="kpi-val text-purple">{{ stats.metrics.upcoming_shifts }}</div>
               <div class="kpi-sub">Scheduled next 30 days</div>
            </div>
         </div>

         <div class="dashboard-grid">

            <div class="dashboard-col">
               <div class="chart-card">
                  <div class="card-header-row">
                     <h3>Top Institutes (by Headcount)</h3>
                     <div class="tooltip-container" data-tooltip="Institutes with the highest number of registered members.">ⓘ</div>
                  </div>
                  <div class="bar-chart scrollable-sm">
                     <div v-for="item in stats.charts.top_institutes" :key="item.institute__name" class="bar-row">
                        <div class="bar-label" :title="item.institute__name">{{ item.institute__name.substring(0, 20) }}...</div>
                        <div class="bar-track"><div class="bar-fill" :style="{ width: (item.count / 1200) * 100 + '%' }"></div></div>
                        <div class="bar-val">{{ item.count }}</div>
                     </div>
                  </div>
               </div>
               <div class="chart-card">
                  <div class="card-header-row">
                     <h3>Workforce Composition</h3>
                     <div class="tooltip-container" data-tooltip="Distribution of personnel by contract (Staff, User, Fellow, PJAS).">ⓘ</div>
                  </div>
                  <div class="bar-chart">
                     <div v-for="item in stats.charts.member_contracts" :key="item.cern_status" class="bar-row">
                        <div class="bar-label">{{ item.cern_status }}</div>
                        <div class="bar-track"><div class="bar-fill purple" :style="{ width: (item.count / 3000) * 100 + '%' }"></div></div>
                        <div class="bar-val">{{ item.count }}</div>
                     </div>
                  </div>
               </div>
            </div>

            <div class="dashboard-col">
               <div class="chart-card">
                  <div class="card-header-row">
                     <h3>Shift Operations (Location)</h3>
                     <div class="tooltip-container" data-tooltip="Operational coverage split between P5 (Point 5), Meyrin Centre, and Remote ROCs.">ⓘ</div>
                  </div>
                  <div class="bar-chart">
                     <div v-for="item in stats.charts.shift_locations" :key="item.location" class="bar-row">
                        <div class="bar-label">{{ item.location }}</div>
                        <div class="bar-track"><div class="bar-fill orange" :style="{ width: (item.count / 1500) * 100 + '%' }"></div></div>
                        <div class="bar-val">{{ item.count }}</div>
                     </div>
                  </div>
               </div>
               <div class="chart-card">
                  <div class="card-header-row">
                     <h3>Top Institutes (Shift Credits)</h3>
                     <div class="tooltip-container" data-tooltip="Total shift credits earned by institute (Essential for M&O authorship qualification).">ⓘ</div>
                  </div>
                  <div class="bar-chart scrollable-sm">
                     <div v-for="item in stats.charts.top_shift_institutes" :key="item.member__institute__name" class="bar-row">
                        <div class="bar-label" :title="item.member__institute__name">{{ item.member__institute__name.substring(0, 20) }}...</div>
                        <div class="bar-track"><div class="bar-fill orange" :style="{ width: (item.count / 1000) * 100 + '%' }"></div></div>
                        <div class="bar-val">{{ item.count }}</div>
                     </div>
                  </div>
               </div>
            </div>

            <div class="dashboard-col">
               <div class="chart-card">
                  <div class="card-header-row">
                     <h3>Analysis Pipeline</h3>
                     <div class="tooltip-container" data-tooltip="Volume of analysis at each stage of the CMS publication lifecycle.">ⓘ</div>
                  </div>
                  <div class="bar-chart">
                     <div v-for="item in stats.charts.paper_phases" :key="item.label" class="bar-row">
                        <div class="bar-label">{{ item.label }}</div>
                        <div class="bar-track"><div class="bar-fill teal" :style="{ width: (item.count / 100) * 100 + '%' }"></div></div>
                        <div class="bar-val">{{ item.count }}</div>
                     </div>
                  </div>
               </div>
               <div class="chart-card">
                  <div class="card-header-row">
                     <h3>Target Journals (Active Analysis)</h3>
                     <div class="tooltip-container" data-tooltip="Target journals for active analysis papers (JHEP, PRL, Nature).">ⓘ</div>
                  </div>
                  <div class="bar-chart">
                     <div v-for="item in stats.charts.journals" :key="item.target_journal" class="bar-row">
                        <div class="bar-label">{{ item.target_journal }}</div>
                        <div class="bar-track"><div class="bar-fill teal" :style="{ width: (item.count / 150) * 100 + '%' }"></div></div>
                        <div class="bar-val">{{ item.count }}</div>
                     </div>
                  </div>
               </div>
            </div>

         </div>
      </div>

      <div v-if="currentApp === 'directory'" class="app-view fade-in">
        <div class="card-container">
          <table class="data-table">
            <thead><tr><th width="60">#</th><th width="100">Contract</th><th>Name</th><th>CERN ID</th><th>Institute</th><th>M&O</th></tr></thead>
            <tbody>
              <tr v-for="(member, index) in members" :key="member.id" @click="openMember(member)">
                <td class="row-num">{{ (currentPage - 1) * 20 + index + 1 }}</td>
                <td><span :class="['status-badge', member.is_active ? 'active' : 'inactive']">{{ member.is_active ? 'Active' : 'Alumni' }}</span></td>
                <td class="fw-bold text-primary">{{ member.last_name }}, {{ member.first_name }}</td>
                <td class="mono">{{ member.cern_id }}</td>
                <td><div class="inst-name">{{ member.institute_name }}</div></td>
                <td><span v-if="member.is_mo_qualified" class="mo-badge">M&O</span><span v-else class="mo-dash">-</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-if="currentApp === 'analysis'" class="app-view fade-in">
        <div class="card-container">
          <table class="data-table">
            <thead><tr><th width="140">Ref Code</th><th width="100">Experiment</th><th>Title</th><th width="180">Lifecycle Phase</th><th width="150">Status</th><th width="100">Team</th></tr></thead>
            <tbody>
              <tr v-for="paper in papers" :key="paper.id" @click="openPaper(paper)">
                <td class="mono fw-bold text-primary">{{ paper.ref_code }}</td>
                <td><span :class="['group-tag', paper.group]">{{ paper.group }}</span></td>
                <td class="title-cell">{{ paper.title }}</td>
                <td><div class="phase-container"><div class="phase-bar"><div :class="['phase-seg', paper.phase >= 0 ? 'on' : '']"></div><div :class="['phase-seg', paper.phase >= 1 ? 'on' : '']"></div><div :class="['phase-seg', paper.phase >= 2 ? 'on' : '']"></div><div :class="['phase-seg', paper.phase >= 3 ? 'on' : '']"></div></div><span class="phase-label">{{ paper.phase_name }}</span></div></td>
                <td><span class="status-text">{{ paper.status_text }}</span></td>
                <td class="text-center"><div class="author-badge-wrapper"><span class="author-badge"><svg class="icon-sm" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"></path></svg> {{ paper.author_count }}</span></div></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <footer class="pagination-footer" v-if="currentApp !== 'dashboard'">
        <span class="page-count">Page {{ currentPage }} of {{ totalPages }}</span>
        <div class="page-actions"><button :disabled="!prevUrl" @click="loadPage(prevUrl, 'prev')" class="btn-page">Previous</button><button :disabled="!nextUrl" @click="loadPage(nextUrl, 'next')" class="btn-page">Next</button></div>
      </footer>

    </main>

    <div v-if="selectedMember" class="modal-overlay" @click.self="closeModals">
      <div class="modal-content split-modal">
        <button class="absolute-close-btn" @click="closeModals"><svg width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"></path></svg></button>

        <div class="modal-body-split">

           <div class="left-panel">

             <div class="tabs-header">
                <button :class="['tab-btn', { active: memberTab === 'profile' }]" @click="memberTab = 'profile'">Profile</button>
                <button :class="['tab-btn', { active: memberTab === 'history' }]" @click="memberTab = 'history'">History</button>
             </div>

             <div v-if="memberTab === 'profile'" class="tab-content fade-in">

                 <div class="profile-header">
                    <div v-if="!isEditing">
                      <h2>{{ selectedMember.last_name }}, {{ selectedMember.first_name }}</h2>
                      <div class="profile-meta-row">
                         <span class="profile-sub">{{ selectedMember.cern_id }}</span>
                         <span class="sep">|</span>
                         <span class="profile-sub">{{ selectedMember.institute_name }}</span>
                      </div>
                      <div class="country-badge">{{ selectedMember.institute_country }}</div>
                    </div>

                    <div v-else class="edit-mode-group">
                      <label class="edit-label">Name</label>
                      <div class="name-inputs">
                        <input v-model="editForm.first_name" class="form-input" placeholder="First Name" />
                        <input v-model="editForm.last_name" class="form-input" placeholder="Last Name" />
                      </div>
                      <div class="read-only-notice">
                        <svg class="lock-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path></svg>
                        <span>ID: {{ selectedMember.cern_id }} &bull; {{ selectedMember.institute_name }}</span>
                      </div>
                    </div>
                 </div>

                 <div class="divider"></div>

                 <div class="vertical-meta">
                   <div class="field-group">
                     <label>Email</label>
                     <div v-if="!isEditing" class="val-text">{{ selectedMember.email }}</div>
                     <input v-else v-model="editForm.email" class="form-input" />
                   </div>
                   <div class="field-group">
                     <label>Contract</label>
                     <div v-if="!isEditing" class="val-text">{{ selectedMember.cern_status }}</div>
                     <select v-else v-model="editForm.cern_status" class="form-select">
                       <option value="USER">USER</option>
                       <option value="STAFF">STAFF</option>
                       <option value="FELLOW">FELLOW</option>
                       <option value="DOCTORAL STUDENT">DOCTORAL STUDENT</option>
                       <option value="PJAS">PJAS</option>
                       <option value="TECHNICAL STUDENT">TECHNICAL STUDENT</option>
                     </select>
                   </div>
                   <div class="field-group">
                     <label>M&O Status</label>
                     <div v-if="!isEditing">
                       <div v-if="selectedMember.is_mo_qualified" class="val-text text-success"><svg class="icon-inline" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg> Qualified</div>
                       <div v-else class="val-text text-muted">Not Qualified</div>
                     </div>
                     <label v-else class="toggle-switch">
                       <input type="checkbox" v-model="editForm.is_mo_qualified">
                       <span class="toggle-slider"></span>
                       <span class="toggle-label">{{ editForm.is_mo_qualified ? 'QUALIFIED' : 'NOT QUALIFIED' }}</span>
                     </label>
                   </div>
                 </div>

                 <div class="section-block">
                   <h3>Technical Qualifications</h3>
                   <div v-if="selectedMember.qualifications && selectedMember.qualifications.length > 0" class="qualifications-list">
                     <div v-for="qual in selectedMember.qualifications" :key="qual.id" class="qual-item">
                        <div class="qual-name">{{ qual.name }}</div>
                        <div class="qual-date">Earned {{ qual.date_earned }}</div>
                     </div>
                   </div>
                   <div v-else class="empty-state">No qualifications recorded.</div>
                 </div>

                 <div class="panel-actions" v-if="isLoggedIn">
                   <button v-if="!isEditing" @click="isEditing = true" class="btn-primary full-width">Edit Profile</button>
                   <div v-else class="edit-actions">
                     <button @click="saveMember" class="btn-primary full-width">Save Changes</button>
                     <button @click="isEditing = false" class="btn-secondary full-width">Cancel</button>
                   </div>
                 </div>
             </div>

             <div v-else class="tab-content fade-in">
                <div class="audit-list">
                   <div v-for="log in selectedMember.auditLogs" :key="log.id" class="audit-item">
                      <div class="audit-date">{{ log.date }}</div>
                      <div class="audit-main">
                         <span class="audit-user">{{ log.user }}</span>
                         <span class="audit-action">{{ log.action }}</span>
                      </div>
                      <div class="audit-detail">{{ log.detail }}</div>
                   </div>
                </div>
             </div>

           </div>

           <div class="right-panel">
             <div class="calendar-header">
               <button @click="changeMonth(-1)" class="cal-btn">&lsaquo;</button>
               <span class="cal-title">{{ calendarHeader }}</span>
               <button @click="changeMonth(1)" class="cal-btn">&rsaquo;</button>
             </div>

             <div class="calendar-grid-header">
               <span>Mon</span><span>Tue</span><span>Wed</span><span>Thu</span><span>Fri</span><span>Sat</span><span>Sun</span>
             </div>

             <div class="calendar-grid">
               <div v-for="(day, idx) in calendarGrid" :key="idx" class="cal-day" @click="openDayManager(day)">
                 <span v-if="day" class="day-num">{{ day }}</span>
                 <div v-if="day" class="day-shifts">
                   <div v-for="shift in getShiftsForDay(day)" :key="shift.id" :class="['shift-bar', shift.type.toLowerCase()]" :title="`${shift.type} at ${shift.location}`"></div>
                 </div>
               </div>
             </div>

             <div class="cal-legend">
                <div class="legend-item"><span class="dot morning"></span> Morning</div>
                <div class="legend-item"><span class="dot evening"></span> Evening</div>
                <div class="legend-item"><span class="dot night"></span> Night</div>
             </div>
           </div>

        </div>
      </div>
    </div>

    <div v-if="showDayModal" class="modal-overlay">
      <div class="login-card">
        <div class="login-header"><h3>Manage Shifts</h3><p>{{ selectedDayData.dayDisplay }}</p></div>

        <div v-if="selectedDayData.shifts.length > 0" class="existing-shifts-list">
           <div v-for="shift in selectedDayData.shifts" :key="shift.id" class="shift-row-item">
              <div class="shift-info"><span :class="['dot', shift.type.toLowerCase()]"></span> <strong>{{ shift.type }}</strong> &mdash; {{ shift.location }}</div>
              <button @click="deleteShift(shift.id)" class="btn-icon-delete"><svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg></button>
           </div>
        </div>
        <div v-else class="empty-state-small">No shifts assigned for this day.</div>

        <div class="divider-line"></div>

        <div class="login-form">
          <div class="input-group"><label>Add New Shift</label><select v-model="newShift.type"><option value="MORNING">Morning (08:00 - 16:00)</option><option value="EVENING">Evening (16:00 - 24:00)</option><option value="NIGHT">Night (00:00 - 08:00)</option></select></div>
          <div class="input-group">
             <select v-model="newShift.location">
                <option value="P5 Control Room (Cessy)">P5 Control Room (Cessy)</option>
                <option value="CMS Centre (Meyrin)">CMS Centre (Meyrin)</option>
                <option value="Fermilab ROC (Remote)">Fermilab ROC (Remote)</option>
                <option value="DESY ROC (Remote)">DESY ROC (Remote)</option>
                <option value="Site 40 Lab">Site 40 Lab</option>
                <option value="Remote (Zoom)">Remote (Zoom)</option>
             </select>
          </div>
        </div>

        <div v-if="shiftError" class="login-alert warn"><div class="alert-content">{{ shiftError }}</div></div>

        <div class="login-actions"><button @click="submitShift" class="btn-primary full-width">Add Shift</button><button @click="showDayModal = false" class="btn-text full-width">Close</button></div>
      </div>
    </div>

    <div v-if="selectedPaper" class="modal-overlay" @click.self="closeModals">
       <div class="modal-content large-modal">
          <div class="modal-header">
             <div class="modal-title-group"><div class="ref-badge">{{ selectedPaper.ref_code }}</div><h2>{{ selectedPaper.title }}</h2></div>
             <button class="close-btn" @click="closeModals"><svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"></path></svg></button>
          </div>
          <div class="modal-body paper-layout">
            <div class="paper-meta-grid">
               <div class="meta-card"><label>Experiment</label><span :class="['group-tag', selectedPaper.group]">{{ selectedPaper.group }}</span></div>
               <div class="meta-card"><label>Started</label><span class="meta-value">{{ selectedPaper.creation_date }}</span></div>
               <div class="meta-card"><label>Journal</label><span class="meta-value">{{ selectedPaper.target_journal || 'N/A' }}</span></div>
               <div class="meta-card"><label>Status</label><span class="status-text bold">{{ selectedPaper.status_text }}</span></div>
            </div>
            <div class="paper-section"><h3>Lifecycle</h3><div class="lifecycle-track"><div :class="['track-step', selectedPaper.phase >= 0 ? 'active' : '']"><div class="step-dot"></div><div class="step-label">Draft / Idea</div></div><div class="track-line"></div><div :class="['track-step', selectedPaper.phase >= 1 ? 'active' : '']"><div class="step-dot"></div><div class="step-label">Analysis</div></div><div class="track-line"></div><div :class="['track-step', selectedPaper.phase >= 2 ? 'active' : '']"><div class="step-dot"></div><div class="step-label">Review</div></div><div class="track-line"></div><div :class="['track-step', selectedPaper.phase >= 3 ? 'active' : '']"><div class="step-dot"></div><div class="step-label">Published</div></div></div></div>
            <div class="paper-section">
               <div class="section-header"><h3>Author Team</h3><span class="count-pill">{{ selectedPaper.author_count }} Members</span></div>
               <div class="authors-grid-clean">
                  <div v-for="author in selectedPaper.authors" :key="author.id" class="author-tile">
                     <div class="author-avatar-sm">{{ author.first_name[0] }}{{ author.last_name[0] }}</div>
                     <div class="author-details"><div class="name">{{ author.last_name }}, {{ author.first_name }}</div><div class="inst">{{ author.institute_name }}</div></div>
                  </div>
               </div>
            </div>
          </div>
       </div>
    </div>

    <div v-if="showLoginModal" class="modal-overlay">
      <div class="login-card">
        <div class="login-header"><h3>Admin Access</h3><p>Please sign in to continue</p></div>
        <div class="login-alert"><svg class="info-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><div class="alert-content">User: <strong>cern</strong> &bull; Pass: <strong>cms123</strong></div></div>
        <div class="login-form">
          <div class="input-group"><label>Username</label><input v-model="loginForm.username" placeholder="Enter username" /></div>
          <div class="input-group"><label>Password</label><input v-model="loginForm.password" type="password" placeholder="Enter password" /></div>
        </div>
        <div class="login-actions"><button @click="login" class="btn-primary full-width">Sign In</button><button @click="showLoginModal = false" class="btn-text full-width">Cancel</button></div>
      </div>
    </div>

  </div>
</template>

<style>body { margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #f3f4f6; }</style>

<style scoped>
/* GLOBAL */
* { box-sizing: border-box; }
.layout { display: flex; height: 100vh; color: #1f2937; overflow: hidden; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 0.85rem; color: #4b5563; }

/* NOTIFICATION TOAST */
.notification-toast {
  position: fixed;
  top: 20px;
  right: 20px;
  padding: 16px 20px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  z-index: 1000;
  display: flex;
  align-items: center;
  min-width: 300px;
  animation: slideIn 0.3s ease-out;
}
.notification-toast.success { background-color: #ecfdf5; border-left: 4px solid #10b981; color: #065f46; }
.notification-toast.error { background-color: #fef2f2; border-left: 4px solid #ef4444; color: #991b1b; }
.toast-content { display: flex; align-items: center; gap: 12px; font-weight: 500; font-size: 0.95rem; }
.toast-icon { width: 24px; height: 24px; }

@keyframes slideIn {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}
.slide-fade-enter-active, .slide-fade-leave-active { transition: all 0.3s ease; }
.slide-fade-enter-from, .slide-fade-leave-to { transform: translateX(10px); opacity: 0; }

/* TOOLTIPS */
.card-header-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.tooltip-container {
  cursor: help;
  color: #9ca3af;
  position: relative;
  display: inline-flex;
  justify-content: center;
  align-items: center;
  font-size: 0.75rem;
  border: 1px solid #e5e7eb;
  border-radius: 50%;
  width: 18px;
  height: 18px;
  background: #f9fafb;
}
.tooltip-container:hover { background: #f3f4f6; color: #4b5563; border-color: #d1d5db; }
.tooltip-container:hover::after {
  content: attr(data-tooltip);
  position: absolute;
  bottom: 130%;
  left: 50%;
  transform: translateX(-50%);
  background: #1f2937;
  color: white;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 0.75rem;
  white-space: nowrap;
  z-index: 100;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
  pointer-events: none;
  font-weight: 500;
}
.tooltip-container:hover::before {
  content: "";
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  border-width: 5px;
  border-style: solid;
  border-color: #1f2937 transparent transparent transparent;
  z-index: 100;
}

.legacy-mode { font-family: "Times New Roman", Times, serif !important; background: #c0c0c0; color: black; }
.legacy-mode .sidebar { background: #333; box-shadow: none; border-right: 2px solid black; }
.legacy-mode .top-bar { background: #c0c0c0; border-bottom: 2px solid black; }
.legacy-mode .main-content { background: #c0c0c0; }
.legacy-mode .card-container { border: 2px solid black; border-radius: 0; box-shadow: 4px 4px 0px #000; }
.legacy-mode .data-table th { background: #ccc; border: 1px solid black; color: black; font-weight: bold; font-family: "Courier New", monospace; text-transform: none; }
.legacy-mode .data-table td { border: 1px solid black; font-family: "Courier New", monospace; color: black; }
.legacy-mode .page-title { font-weight: bold; text-decoration: underline; font-family: "Courier New", monospace; }

/* LEGACY DASHBOARD */
.legacy-mode .kpi-card,
.legacy-mode .chart-card {
  border-radius: 0 !important;
  border: 2px solid black !important;
  box-shadow: 4px 4px 0px #000 !important;
  background: white !important;
}
.legacy-mode .kpi-label {
  font-family: "Times New Roman", serif;
  font-weight: bold;
  color: black;
  text-decoration: underline;
  letter-spacing: 0;
}
.legacy-mode .kpi-val {
  font-family: "Courier New", monospace;
  color: #000080;
}
.legacy-mode .bar-track {
  background: white !important;
  border: 1px solid black !important;
  border-radius: 0 !important;
  height: 12px !important;
}
.legacy-mode .bar-fill {
  border-radius: 0 !important;
  background: #000080 !important;
}
.legacy-mode .bar-label {
  font-family: "Courier New", monospace;
  color: black;
}

/* LEGACY MODALS & POPUPS */
.legacy-mode .modal-content,
.legacy-mode .login-card,
.legacy-mode .export-menu {
  border-radius: 0 !important;
  border: 2px solid #000 !important;
  box-shadow: 6px 6px 0px #000 !important;
  background: #d4d0c8 !important;
  font-family: "Times New Roman", serif !important;
}

.legacy-mode .modal-header,
.legacy-mode .login-header {
  background: #000080;
  color: white !important;
  padding: 8px 12px;
  border-bottom: 2px solid white;
}
.legacy-mode .modal-title h2,
.legacy-mode .login-header h3,
.legacy-mode .login-header p {
  color: white !important;
  margin: 0;
  font-family: "Courier New", monospace;
}

/* LEGACY BUTTONS */
.legacy-mode button,
.legacy-mode .btn-primary,
.legacy-mode .btn-secondary,
.legacy-mode .cal-btn,
.legacy-mode .close-btn,
.legacy-mode .absolute-close-btn {
  border-radius: 0 !important;
  border: 2px outset #fff !important;
  background-color: #c0c0c0 !important;
  color: black !important;
  font-family: "Courier New", monospace !important;
  box-shadow: none !important;
  text-transform: uppercase;
  font-weight: bold;
}
.legacy-mode button:active,
.legacy-mode .btn-primary:active {
  border: 2px inset #fff !important;
}

/* LEGACY INPUTS */
.legacy-mode input,
.legacy-mode select {
  border-radius: 0 !important;
  border: 2px inset #fff !important;
  background-color: white !important;
  font-family: "Courier New", monospace !important;
  box-shadow: none !important;
}

/* LEGACY LEFTOVERS */
.legacy-mode .left-panel,
.legacy-mode .right-panel,
.legacy-mode .paper-layout {
  background: #d4d0c8 !important;
  color: black !important;
}
.legacy-mode .meta-card {
  border: 1px solid black !important;
  box-shadow: none !important;
  border-radius: 0 !important;
}
.legacy-mode .qual-item, .legacy-mode .audit-item {
  border: 1px solid black !important;
  background: white !important;
  border-radius: 0 !important;
}

/* LEGACY MODE OVERRIDES FOR NEW COLORS */
.legacy-mode .bar-fill.orange { background: #800000 !important; }
.legacy-mode .bar-fill.purple { background: #800080 !important; }
.legacy-mode .bar-fill.teal { background: #008080 !important; }

/* LEGACY TOGGLE SWITCH */
.legacy-toggle-box { padding: 12px 0; border-top: 1px solid rgba(255,255,255,0.1); margin-top: auto; }
.toggle-switch-small { display: flex; align-items: center; gap: 8px; cursor: pointer; color: rgba(255,255,255,0.7); font-size: 0.8rem; }
.toggle-switch-small input { display: none; }
.slider-small { width: 28px; height: 16px; background: rgba(255,255,255,0.2); border-radius: 10px; position: relative; transition: 0.2s; }
.slider-small::before { content:""; position: absolute; width: 12px; height: 12px; background: white; border-radius: 50%; top: 2px; left: 2px; transition: 0.2s; }
.toggle-switch-small input:checked + .slider-small { background: #4caf50; }
.toggle-switch-small input:checked + .slider-small::before { transform: translateX(12px); }

/* SIDEBAR */
.sidebar { width: 260px; background: #0053A1; color: white; display: flex; flex-direction: column; padding: 24px; z-index: 10; height: 100vh; box-shadow: 4px 0 10px rgba(0,0,0,0.1); }
.brand { display: flex; align-items: center; gap: 12px; margin-bottom: 40px; }
.logo-box { background: white; color: #0053A1; font-weight: 900; padding: 4px 8px; border-radius: 4px; font-size: 0.9rem; letter-spacing: 0.5px; }
.brand h2 { margin: 0; font-size: 1.2rem; letter-spacing: 1px; font-weight: 600; color: white; }
.nav-section { flex: 1; }
.nav-label { font-size: 0.7rem; text-transform: uppercase; color: rgba(255,255,255,0.6); margin-bottom: 12px; font-weight: 600; letter-spacing: 0.05em; }
.nav-item { display: flex; align-items: center; gap: 12px; background: transparent; border: none; color: rgba(255,255,255,0.8); width: 100%; text-align: left; padding: 10px 12px; font-size: 0.95rem; cursor: pointer; border-radius: 6px; margin-bottom: 4px; transition: all 0.2s; }
.nav-item:hover { background: rgba(255,255,255,0.1); color: white; }
.nav-item.active { background: #003c75; color: white; font-weight: 600; box-shadow: inset 3px 0 0 white; border-radius: 0 6px 6px 0; }
.icon { width: 20px; height: 20px; opacity: 0.9; }
.auth-box { margin-top: 12px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.2); }
.user-info { display: flex; align-items: center; gap: 12px; }
.avatar-small { width: 36px; height: 36px; background: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 0.9rem; color: #0053A1; }
.user-text { display: flex; flex-direction: column; font-size: 0.85rem; }
.link-logout { background: none; border: none; color: rgba(255,255,255,0.7); padding: 0; font-size: 0.75rem; text-align: left; cursor: pointer; text-decoration: underline; margin-top: 2px; }
.btn-login-side { display: flex; align-items: center; gap: 8px; background: rgba(0,0,0,0.2); color: white; border: 1px solid rgba(255,255,255,0.2); padding: 8px 16px; border-radius: 6px; font-size: 0.9rem; cursor: pointer; width: 100%; transition: background 0.2s; }

/* MAIN */
.main-content { flex: 1; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
.top-bar { background: white; padding: 0 32px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e5e7eb; height: 64px; flex-shrink: 0; }
.page-title { margin: 0; font-size: 1.4rem; color: #1f2937; }
.left-controls { display: flex; gap: 16px; align-items: center; }
.header-divider { width: 1px; height: 24px; background: #e5e7eb; }
.search-wrapper { display: flex; align-items: center; background: #f9fafb; border: 1px solid #e5e7eb; padding: 8px 12px; border-radius: 6px; width: 350px; transition: border 0.2s; }
.search-wrapper:focus-within { border-color: #0053A1; box-shadow: 0 0 0 2px rgba(0, 83, 161, 0.1); }
.search-icon { width: 18px; height: 18px; color: #9ca3af; margin-right: 10px; }
.search-wrapper input { border: none; background: transparent; outline: none; width: 100%; font-size: 0.9rem; color: #1f2937; }

/* CONTROLS RIGHT */
.controls-right { display: flex; align-items: center; gap: 12px; }
.sort-control { display: flex; align-items: center; gap: 8px; }
.sort-control .label { font-size: 0.75rem; color: #6b7280; font-weight: 600; text-transform: uppercase; }
.sort-select { padding: 6px 10px; border: 1px solid #d1d5db; border-radius: 4px; font-size: 0.85rem; color: #374151; background: white; cursor: pointer; }
.btn-export { display: flex; align-items: center; gap: 6px; background: white; border: 1px solid #d1d5db; color: #374151; padding: 6px 12px; border-radius: 4px; font-size: 0.85rem; cursor: pointer; font-weight: 500; position: relative; }
.btn-export:hover { background: #f3f4f6; border-color: #9ca3af; }
.export-wrapper { position: relative; }
.export-menu { position: absolute; top: 100%; right: 0; background: white; border: 1px solid #e5e7eb; border-radius: 6px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); margin-top: 8px; z-index: 50; width: 220px; overflow: hidden; }
.menu-item { padding: 12px 16px; cursor: pointer; transition: background 0.2s; display: flex; flex-direction: column; gap: 2px; }
.menu-item:hover { background: #f9fafb; }
.menu-item span { font-size: 0.9rem; font-weight: 600; color: #374151; }
.menu-item small { font-size: 0.75rem; color: #9ca3af; }
.icon-sm { width: 16px; height: 16px; }

/* FILTER PANEL */
.btn-filter { display: flex; align-items: center; gap: 6px; padding: 8px 12px; border: 1px solid #d1d5db; background: white; border-radius: 6px; cursor: pointer; font-size: 0.9rem; color: #4b5563; }
.btn-filter.active { background: #eff6ff; border-color: #0053A1; color: #0053A1; }
.icon-filter { width: 18px; height: 18px; }
.filter-panel { background: white; border-bottom: 1px solid #e5e7eb; padding: 15px 32px; box-shadow: 0 4px 6px -4px rgba(0,0,0,0.05); z-index: 20; position: relative; }
.filter-row { display: flex; gap: 20px; align-items: flex-end; }
.filter-group { display: flex; flex-direction: column; gap: 5px; }
.filter-group label { font-size: 0.75rem; font-weight: 700; color: #6b7280; text-transform: uppercase; }
.filter-input { padding: 6px 10px; border: 1px solid #d1d5db; border-radius: 4px; font-size: 0.9rem; width: 180px; outline: none; }
.filter-input:focus { border-color: #0053A1; }
.filter-group select { padding: 6px 10px; border: 1px solid #d1d5db; border-radius: 4px; font-size: 0.9rem; min-width: 150px; }
.btn-clear { background: none; border: none; color: #6b7280; text-decoration: underline; cursor: pointer; font-size: 0.85rem; margin-bottom: 8px; }
.fade-in-down { animation: fadeInDown 0.2s ease-out; }
@keyframes fadeInDown { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } }

/* TABLE */
.app-view { flex: 1; padding: 24px 32px; overflow-y: auto; background: #f3f4f6; }
.card-container { background: white; border-radius: 8px; border: 1px solid #e5e7eb; overflow: hidden; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th { background: #f9fafb; text-align: left; padding: 12px 20px; font-size: 0.75rem; text-transform: uppercase; color: #6b7280; font-weight: 600; letter-spacing: 0.05em; border-bottom: 1px solid #e5e7eb; height: 48px; }
.data-table td { padding: 12px 20px; border-bottom: 1px solid #f3f4f6; font-size: 0.9rem; color: #374151; vertical-align: middle; height: 56px; }
.data-table tr:hover { background: #f8fafc; cursor: pointer; }

/* DASHBOARD STYLES */
.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 24px; margin-bottom: 32px; }

/* 3-COLUMN DASHBOARD GRID */
.dashboard-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; }
.dashboard-col { display: flex; flex-direction: column; gap: 24px; }

/* SCROLLABLE CHARTS */
.scrollable-sm { max-height: 200px; overflow-y: auto; }

/* COLORS */
.text-purple { color: #7c3aed; }
.bar-fill.orange { background: #f97316; }

.kpi-card { background: white; padding: 24px; border-radius: 8px; border: 1px solid #e5e7eb; box-shadow: 0 1px 2px rgba(0,0,0,0.02); }
.kpi-label { font-size: 0.85rem; color: #6b7280; text-transform: uppercase; font-weight: 600; letter-spacing: 0.05em; margin-bottom: 0; }
.kpi-val { font-size: 2rem; font-weight: 800; color: #1f2937; margin-bottom: 4px; }
.kpi-sub { font-size: 0.9rem; color: #9ca3af; }
.charts-grid-2x2 { display: grid; grid-template-columns: repeat(2, 1fr); gap: 24px; }
.chart-card { background: white; padding: 24px; border-radius: 8px; border: 1px solid #e5e7eb; }
.chart-card h3 { margin: 0; font-size: 1rem; color: #374151; }
.bar-chart { display: flex; flex-direction: column; gap: 12px; }
.bar-chart.scrollable { max-height: 250px; overflow-y: auto; padding-right: 5px; }
.bar-row { display: flex; align-items: center; gap: 12px; }
.bar-label { width: 140px; font-size: 0.8rem; color: #6b7280; text-align: right; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.bar-track { flex: 1; height: 8px; background: #f3f4f6; border-radius: 4px; overflow: hidden; }
.bar-fill { height: 100%; background: #0053A1; border-radius: 4px; animation: grow 1s ease-out; }
.bar-fill.blue { background: #3b82f6; }
.bar-fill.purple { background: #8b5cf6; }
.bar-fill.teal { background: #14b8a6; }
.bar-val { width: 40px; font-size: 0.85rem; font-weight: 600; color: #1f2937; }
.text-success { color: #059669; }
.text-blue { color: #0053A1; }
@keyframes grow { from { width: 0; } }

/* BADGES */
.status-badge { padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }
.status-badge.active { background: #ecfdf5; color: #047857; }
.status-badge.inactive { background: #f3f4f6; color: #6b7280; }
.mo-badge { background: #fffff0; border: 1px solid #fde047; color: #b45309; padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; font-weight: bold; }
.mo-dash { color: #d1d5db; }
.group-tag { display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; font-weight: 700; color: white; text-align: center; min-width: 55px; }
.group-tag.ATLAS { background: #0b80c3; } .group-tag.CMS { background: #d92d27; } .group-tag.ALICE { background: #f26222; } .group-tag.LHCb { background: #003e73; }
.group-tag.TOTEM { background: #ffcc00; color: #333; } .group-tag.LHCf { background: #666; } .group-tag.MOEDAL { background: #8e44ad; } .group-tag.FASER { background: #27ae60; } .group-tag.SND { background: #2c3e50; }

.phase-bar { display: flex; gap: 2px; height: 4px; width: 80px; }
.phase-seg { flex: 1; background: #e5e7eb; border-radius: 1px; }
.phase-seg.on { background: #0053A1; }
.author-badge-wrapper { display: flex; justify-content: center; }
.author-badge { background: #f3f4f6; color: #4b5563; padding: 4px 10px; border-radius: 12px; font-size: 0.8rem; font-weight: 500; display: inline-flex; align-items: center; gap: 6px; }
.pagination-footer { padding: 12px 32px; background: white; border-top: 1px solid #e5e7eb; display: flex; justify-content: space-between; align-items: center; height: 60px; flex-shrink: 0; }
.btn-page { padding: 6px 12px; border: 1px solid #d1d5db; background: white; border-radius: 4px; cursor: pointer; font-size: 0.85rem; color: #374151; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.6); backdrop-filter: blur(2px); display: flex; justify-content: center; align-items: center; z-index: 50; }
.modal-content { background: white; width: 500px; border-radius: 12px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25); overflow: hidden; display: flex; flex-direction: column; max-height: 90vh; position: relative; }
.modal-content.wide-modal { width: 600px; max-height: 90vh; }
.modal-content.large-modal { width: 800px; max-height: 90vh; }
.modal-content.split-modal { width: 90vw; max-width: 1400px; height: 90vh; max-height: 900px; }
.modal-header { padding: 24px; border-bottom: 1px solid #e5e7eb; display: flex; justify-content: space-between; align-items: flex-start; flex-shrink: 0; background: white; }
.modal-title-group { display: flex; flex-direction: column; gap: 6px; }
.modal-title h2 { margin: 0; font-size: 1.25rem; color: #111827; }
.modal-subtitle { font-size: 0.9rem; color: #6b7280; margin-top: 4px; display: block; }
.close-btn { background: white; border: 1px solid #e5e7eb; color: #6b7280; cursor: pointer; padding: 0; border-radius: 8px; display: flex; align-items: center; justify-content: center; transition: all 0.2s; width: 36px; height: 36px; }
.close-btn:hover { background: #f3f4f6; color: #ef4444; border-color: #fee2e2; }
.absolute-close-btn { position: absolute; top: 15px; right: 15px; background: white; border: 1px solid #e5e7eb; color: #6b7280; width: 32px; height: 32px; border-radius: 6px; display: flex; align-items: center; justify-content: center; cursor: pointer; z-index: 20; transition: all 0.2s; }
.absolute-close-btn:hover { color: #ef4444; border-color: #fee2e2; background: #fff1f2; }
.modal-body { padding: 0; overflow-y: auto; }
.modal-body-scroll { padding: 24px; }
.modal-body-split { display: grid; grid-template-columns: 320px 1fr; height: 100%; }
.left-panel { padding: 24px; border-right: 1px solid #e5e7eb; background: #f9fafb; display: flex; flex-direction: column; gap: 20px; overflow-y: auto; padding-top: 40px; }
.right-panel { padding: 70px 32px 32px 32px; background: white; display: flex; flex-direction: column; position: relative; }
.panel-actions { margin-top: auto; }
.edit-actions { display: flex; flex-direction: column; gap: 8px; width: 100%; align-items: stretch; }
.modal-footer { padding: 20px 24px; background: #f9fafb; border-top: 1px solid #e5e7eb; display: flex; justify-content: flex-end; flex-shrink: 0; }
.btn-primary { background: #0053A1; color: white; border: none; padding: 10px 16px; border-radius: 4px; cursor: pointer; width: 100%; margin: 0; display: flex; justify-content: center; align-items: center; transition: background 0.2s; font-weight: 600; font-size: 0.9rem; }
.btn-primary:hover { background: #003c75; }
.btn-secondary { background: white; color: #374151; border: 1px solid #d1d5db; padding: 10px 16px; border-radius: 4px; cursor: pointer; width: 100%; margin: 0; display: flex; justify-content: center; align-items: center; font-weight: 500; font-size: 0.9rem; }
.btn-secondary:hover { background: #f9fafb; border-color: #9ca3af; }
.full-width { width: 100%; margin-bottom: 8px; }
.ref-badge { display: inline-block; background: #eff6ff; color: #0053A1; font-family: monospace; padding: 2px 6px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; width: fit-content; }
.success-text { color: #059669; font-weight: 600; display: flex; align-items: center; gap: 6px; }
.icon-inline { width: 18px; height: 18px; }
.muted-text { color: #9ca3af; }

/* LEFT PANEL PROFILE */
.profile-header h2 { margin: 0 0 8px 0; font-size: 1.5rem; color: #1f2937; }
.profile-meta-row { display: flex; gap: 8px; color: #6b7280; font-size: 0.9rem; align-items: center; }
.sep { color: #e5e7eb; }
.country-badge { margin-top: 8px; display: inline-block; background: #e0e7ff; color: #3730a3; padding: 4px 10px; border-radius: 12px; font-weight: 600; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; }
.divider { height: 1px; background: #e5e7eb; margin: 10px 0; }

/* TABS */
.tabs-header { display: flex; border-bottom: 1px solid #e5e7eb; margin-bottom: 16px; }
.tab-btn { flex: 1; padding: 10px; background: none; border: none; border-bottom: 2px solid transparent; font-weight: 600; color: #6b7280; cursor: pointer; transition: all 0.2s; }
.tab-btn:hover { color: #0053A1; background: #f0f9ff; }
.tab-btn.active { color: #0053A1; border-bottom-color: #0053A1; }
.tab-content { display: flex; flex-direction: column; gap: 20px; flex: 1; overflow-y: auto; }

/* AUDIT LOG */
.audit-list { display: flex; flex-direction: column; gap: 12px; }
.audit-item { padding: 12px; background: white; border: 1px solid #e5e7eb; border-radius: 6px; border-left: 3px solid #0053A1; }
.audit-date { font-size: 0.7rem; color: #9ca3af; margin-bottom: 4px; }
.audit-main { display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 4px; }
.audit-user { font-weight: 600; color: #374151; }
.audit-action { color: #0053A1; font-weight: 500; }
.audit-detail { font-size: 0.8rem; color: #4b5563; font-style: italic; }

/* QUALIFICATIONS CARD LIST */
.qualifications-list { display: flex; flex-direction: column; gap: 8px; }
.qual-item { padding: 10px 12px; background: white; border: 1px solid #e5e7eb; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; }
.qual-name { font-weight: 600; color: #374151; font-size: 0.9rem; }
.qual-date { font-size: 0.75rem; color: #9ca3af; }

/* VERTICAL META */
.vertical-meta { display: flex; flex-direction: column; gap: 12px; border-bottom: 1px solid #e5e7eb; padding-bottom: 20px; }
.field-group label { display: block; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; color: #64748b; margin-bottom: 4px; }
.val-text { font-size: 0.95rem; font-weight: 500; color: #1e293b; }
.text-success { color: #059669; display: flex; align-items: center; gap: 6px; }

/* CALENDAR STYLES */
.calendar-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.cal-btn { background: white; border: 1px solid #e5e7eb; border-radius: 4px; width: 32px; height: 32px; cursor: pointer; display: flex; align-items: center; justify-content: center; color: #6b7280; font-size: 1.2rem; transition: all 0.2s; }
.cal-btn:hover { background: #f9fafb; color: #0053A1; border-color: #d1d5db; }
.cal-title { font-weight: 700; color: #374151; font-size: 1.1rem; }
.calendar-grid-header { display: grid; grid-template-columns: repeat(7, 1fr); text-align: center; font-size: 0.75rem; font-weight: 600; color: #9ca3af; margin-bottom: 8px; text-transform: uppercase; }
.calendar-grid { display: grid !important; grid-template-columns: repeat(7, 1fr) !important; grid-auto-rows: 1fr; gap: 1px; background: #e5e7eb; border: 1px solid #e5e7eb; flex: 1; min-height: 300px; width: 100%; }
.cal-day { background: white; min-height: 60px; padding: 4px; display: flex; flex-direction: column; gap: 2px; cursor: pointer; transition: background 0.2s; position: relative; }
.cal-day:hover { background: #f8fafc; z-index: 2; }
.day-num { font-size: 0.75rem; color: #9ca3af; font-weight: 500; }
.day-shifts { display: flex; flex-direction: column; gap: 2px; }
.shift-bar { height: 6px; border-radius: 3px; width: 100%; cursor: help; transition: opacity 0.2s; }
.shift-bar:hover { opacity: 0.7; }
.shift-bar.morning { background: #f59e0b; }
.shift-bar.evening { background: #3b82f6; }
.shift-bar.night { background: #1e293b; }
.cal-legend { display: flex; gap: 24px; margin-top: 16px; font-size: 0.8rem; color: #6b7280; justify-content: center; }
.legend-item { display: flex; align-items: center; gap: 8px; }
.dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.dot.morning { background: #f59e0b; } .dot.evening { background: #3b82f6; } .dot.night { background: #1e293b; }

/* SHIFT MANAGER LIST */
.existing-shifts-list { margin-bottom: 20px; display: flex; flex-direction: column; gap: 8px; max-height: 150px; overflow-y: auto; border: 1px solid #f3f4f6; border-radius: 6px; padding: 4px; }
.shift-row-item { display: flex; justify-content: space-between; align-items: center; background: #f9fafb; padding: 10px 12px; border-radius: 6px; border: 1px solid #e5e7eb; margin-bottom: 6px; }
.shift-info { font-size: 0.9rem; color: #374151; display: flex; align-items: center; gap: 8px; }
.btn-icon-delete { background: none; border: none; color: #9ca3af; cursor: pointer; padding: 4px 8px; border-radius: 4px; font-weight: bold; transition: all 0.2s; }
.btn-icon-delete:hover { color: #ef4444; background: #fee2e2; }
.empty-state-small { font-size: 0.85rem; color: #9ca3af; font-style: italic; text-align: center; margin-bottom: 20px; }
.divider-line { height: 1px; background: #e5e7eb; margin: 0 0 20px 0; }

/* LOGIN & ADD SHIFT STYLING */
.login-card { background: white; width: 380px; padding: 32px; border-radius: 12px; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1); text-align: left; }
.login-header h3 { margin: 0 0 8px 0; color: #111827; font-size: 1.5rem; }
.login-header p { margin: 0 0 24px 0; color: #6b7280; font-size: 0.9rem; }
.login-alert { background: #eff6ff; border: 1px solid #dbeafe; padding: 12px; border-radius: 6px; display: flex; gap: 12px; align-items: center; margin-bottom: 24px; font-size: 0.85rem; color: #1e40af; }
.login-alert.warn { background: #fff7ed; border-color: #ffedd5; color: #c2410c; }
.info-icon { width: 20px; height: 20px; flex-shrink: 0; }
.input-group { margin-bottom: 16px; }
.input-group label { display: block; font-size: 0.85rem; font-weight: 500; color: #374151; margin-bottom: 6px; }
.input-group input, .input-group select { width: 100%; padding: 10px 12px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.95rem; outline: none; transition: border-color 0.2s; background: white; }
.input-group input:focus, .input-group select:focus { border-color: #0053A1; box-shadow: 0 0 0 2px rgba(0, 83, 161, 0.1); }
.btn-text { background: none; border: none; color: #6b7280; cursor: pointer; margin-top: 8px; font-size: 0.9rem; text-decoration: underline; }
.btn-text:hover { color: #374151; }
.login-form { margin-top: 20px; }
.login-actions { margin-top: 24px; display: flex; flex-direction: column; gap: 12px; }

/* FORM ELEMENTS */
.form-input, .form-select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 0.9rem;
  background: white;
  margin-top: 4px;
}
.form-input:focus, .form-select:focus {
  border-color: #0053A1;
  outline: none;
  box-shadow: 0 0 0 2px rgba(0, 83, 161, 0.1);
}
.name-inputs { display: flex; gap: 8px; margin-bottom: 8px; }
.edit-label { font-size: 0.75rem; color: #6b7280; font-weight: 600; text-transform: uppercase; }
.read-only-notice { font-size: 0.75rem; color: #9ca3af; display: flex; align-items: center; gap: 6px; background: #f3f4f6; padding: 6px; border-radius: 4px; }
.lock-icon { width: 12px; height: 12px; }

/* TOGGLE SWITCH  */
.toggle-switch {
  display: flex;
  align-items: center;
  cursor: pointer;
  gap: 20px;
  margin-top: 8px;
}
.toggle-switch input {
  display: none;
}
.toggle-slider {
  width: 36px;
  min-width: 36px;
  height: 20px;
  background-color: #e5e7eb;
  border-radius: 20px;
  position: relative;
  transition: 0.3s;
  display: inline-block;
  flex-shrink: 0;
}
.toggle-slider::before {
  content: "";
  position: absolute;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: white;
  top: 2px;
  left: 2px;
  transition: 0.3s;
  box-shadow: 0 1px 2px rgba(0,0,0,0.2);
}
.toggle-switch input:checked + .toggle-slider {
  background-color: #0053A1;
}
.toggle-switch input:checked + .toggle-slider::before {
  transform: translateX(16px);
}
.toggle-label {
  font-size: 0.9rem;
  font-weight: 500;
  color: #374151;
  margin-left: 12px;
  white-space: nowrap;
}

/* FIXED: PAPER MODAL LAYOUT */
.paper-layout { padding: 32px; background: #fafafa; }
.paper-meta-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 24px; margin-bottom: 32px; }
.meta-card { background: white; padding: 16px; border-radius: 8px; border: 1px solid #e5e7eb; box-shadow: 0 1px 2px rgba(0,0,0,0.02); display: flex; flex-direction: column; gap: 4px; align-items: flex-start !important; }
.meta-card label { display: block; font-size: 0.7rem; font-weight: 700; color: #6b7280; text-transform: uppercase; margin-bottom: 6px; }
.meta-value { font-size: 0.95rem; color: #111827; font-weight: 500; }

.paper-section { margin-top: 32px; }
.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.paper-section h3 { font-size: 0.9rem; font-weight: 700; color: #374151; margin: 0; text-transform: uppercase; letter-spacing: 0.05em; }
.count-pill { background: #e0e7ff; color: #3730a3; padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }

.authors-grid-clean { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; max-height: 250px; overflow-y: auto; padding: 2px; }
.author-tile { display: flex; align-items: center; gap: 12px; padding: 12px; background: white; border: 1px solid #e5e7eb; border-radius: 8px; box-shadow: 0 1px 2px rgba(0,0,0,0.02); transition: all 0.2s; }
.author-tile:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.05); transform: translateY(-1px); border-color: #d1d5db; }
.author-avatar-sm { width: 36px; height: 36px; background: #0053A1; color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.85rem; font-weight: bold; flex-shrink: 0; }
.author-details { overflow: hidden; }
.author-details .name { font-size: 0.9rem; font-weight: 600; color: #1f2937; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.author-details .inst { font-size: 0.75rem; color: #6b7280; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-top: 2px; }

/* LIFECYCLE TRACK */
.lifecycle-track { display: flex; align-items: center; justify-content: space-between; margin: 24px 0; padding: 0 10px; }
.track-step { display: flex; flex-direction: column; align-items: center; gap: 8px; position: relative; z-index: 2; flex: 1; }
.step-dot { width: 14px; height: 14px; background: #e5e7eb; border-radius: 50%; border: 3px solid white; box-shadow: 0 0 0 1px #d1d5db; transition: all 0.3s; }
.step-label { font-size: 0.75rem; color: #9ca3af; font-weight: 600; transition: color 0.3s; text-align: center; }
.track-step.active .step-dot { background: #0053A1; box-shadow: 0 0 0 3px #bfdbfe; border-color: #0053A1; }
.track-step.active .step-label { color: #0053A1; }
.track-line { flex: 1; height: 2px; background: #e5e7eb; margin: 0 10px; position: relative; top: -14px; z-index: 1; }
</style>