import { Link, NavLink, Route, Routes } from 'react-router-dom';
import { Brain, CheckSquare, GitBranch, InboxIcon, Lightbulb, MessageSquareText, Settings as SettingsIcon, Sparkles } from 'lucide-react';
import Inbox from './pages/Inbox';
import ItemDetail from './pages/ItemDetail';
import Ask from './pages/Ask';
import Graph from './pages/Graph';
import Memories from './pages/Memories';
import Projects from './pages/Projects';
import Ideas from './pages/Ideas';
import Tasks from './pages/Tasks';
import Decisions from './pages/Decisions';
import OpenQuestions from './pages/OpenQuestions';
import Settings from './pages/Settings';

function navClass({ isActive }: { isActive: boolean }) {
  return `flex items-center gap-2 rounded-md px-3 py-2 text-sm ${isActive ? 'bg-slate-900 text-white' : 'text-slate-700 hover:bg-slate-200'}`;
}

export default function App() {
  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-3">
          <Link to="/" className="flex items-center gap-2 text-base font-semibold">
            <Brain size={20} />
            Second Brain Inbox
          </Link>
          <nav className="flex items-center gap-1">
            <NavLink to="/" className={navClass}>
              <InboxIcon size={16} />
              Inbox
            </NavLink>
            <NavLink to="/memories" className={navClass}>Memories</NavLink>
            <NavLink to="/projects" className={navClass}>Projects</NavLink>
            <NavLink to="/ideas" className={navClass}>
              <Sparkles size={16} />
              Ideas
            </NavLink>
            <NavLink to="/tasks" className={navClass}>
              <CheckSquare size={16} />
              Tasks
            </NavLink>
            <NavLink to="/decisions" className={navClass}>
              <Lightbulb size={16} />
              Decisions
            </NavLink>
            <NavLink to="/open-questions" className={navClass}>Questions</NavLink>
            <NavLink to="/ask" className={navClass}>
              <MessageSquareText size={16} />
              Ask
            </NavLink>
            <NavLink to="/graph" className={navClass}>
              <GitBranch size={16} />
              Graph
            </NavLink>
            <NavLink to="/settings" className={navClass}>
              <SettingsIcon size={16} />
              Settings
            </NavLink>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-5 py-5">
        <Routes>
          <Route path="/" element={<Inbox />} />
          <Route path="/items/:id" element={<ItemDetail />} />
          <Route path="/memories" element={<Memories />} />
          <Route path="/projects" element={<Projects />} />
          <Route path="/ideas" element={<Ideas />} />
          <Route path="/tasks" element={<Tasks />} />
          <Route path="/decisions" element={<Decisions />} />
          <Route path="/open-questions" element={<OpenQuestions />} />
          <Route path="/ask" element={<Ask />} />
          <Route path="/graph" element={<Graph />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  );
}
