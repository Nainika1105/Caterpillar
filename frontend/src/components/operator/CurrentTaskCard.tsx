import React from 'react';
import { useFleet } from '../../context/FleetContext';
import { useAuth } from '../../context/AuthContext';
import { Task } from '../../types';
import { Play, Pause, CheckCircle2, Clock, Target, FileText, ChevronRight } from 'lucide-react';

export const CurrentTaskCard: React.FC = () => {
  const { tasks, updateTaskStatus } = useFleet();
  const { activeMachine } = useAuth();

  // Find task assigned to active machine
  const machineTasks = tasks.filter(t => t.machine_id === activeMachine.machine_id);
  const activeTask = machineTasks.find(t => t.status === 'in_progress' || t.status === 'paused') || machineTasks[0];
  const queuedTasks = machineTasks.filter(t => t.task_id !== activeTask?.task_id);

  if (!activeTask) {
    return (
      <div className="bg-cat-panel border border-cat-border rounded-xl p-5 shadow-cat text-center py-8">
        <p className="text-slate-400 font-mono text-sm">No tasks currently assigned to unit {activeMachine.machine_id}.</p>
      </div>
    );
  }

  const isRunning = activeTask.status === 'in_progress';

  return (
    <div className="bg-cat-panel border border-cat-border rounded-xl p-5 shadow-cat">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-cat-border pb-3 mb-4">
        <div className="flex items-center space-x-2">
          <span className="px-2 py-0.5 bg-cat-dark border border-cat-yellow/30 font-mono font-bold text-xs text-cat-yellow rounded">
            {activeTask.task_id}
          </span>
          <span className={`px-2 py-0.5 rounded text-[11px] font-mono uppercase font-bold ${
            isRunning 
              ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' 
              : activeTask.status === 'completed'
                ? 'bg-blue-950 text-blue-400 border border-blue-800'
                : 'bg-amber-950 text-amber-400 border border-amber-800'
          }`}>
            ● {activeTask.status.replace('_', ' ')}
          </span>
        </div>

        <div className="flex items-center space-x-2 text-xs font-mono text-slate-400">
          <Clock className="w-3.5 h-3.5 text-cat-yellow" />
          <span>PLANNED: {activeTask.planned_duration_min} MINS</span>
        </div>
      </div>

      {/* Task Headline & Goal */}
      <div className="mb-4">
        <h3 className="text-lg font-bold text-white tracking-wide uppercase font-sans">
          {activeTask.task_type.replace(/_/g, ' ')}
        </h3>
        <p className="text-xs text-slate-300 mt-1 font-mono leading-relaxed">
          {activeTask.notes || 'Execute designated cut and grade parameters according to project survey points.'}
        </p>
      </div>

      {/* Target Metrics */}
      <div className="grid grid-cols-2 gap-3 mb-5">
        <div className="bg-cat-dark p-3 rounded-lg border border-cat-border">
          <div className="flex items-center space-x-1.5 text-slate-400 text-xs font-mono">
            <Target className="w-3.5 h-3.5 text-cat-yellow" />
            <span>TARGET VOLUME</span>
          </div>
          <div className="text-xl font-bold font-mono text-white mt-1">
            {activeTask.quantity} <span className="text-xs text-slate-400 font-sans">{activeTask.quantity_unit}</span>
          </div>
        </div>

        <div className="bg-cat-dark p-3 rounded-lg border border-cat-border">
          <div className="flex items-center space-x-1.5 text-slate-400 text-xs font-mono">
            <Clock className="w-3.5 h-3.5 text-cat-yellow" />
            <span>EST. TIME REMAINING</span>
          </div>
          <div className="text-xl font-bold font-mono text-cat-yellow mt-1">
            {isRunning ? '65 mins' : 'Standby'}
          </div>
        </div>
      </div>

      {/* Large Tactile Cab Action Buttons */}
      <div className="grid grid-cols-2 gap-3">
        {isRunning ? (
          <button
            onClick={() => updateTaskStatus(activeTask.task_id, 'paused')}
            className="flex items-center justify-center space-x-2 py-3.5 px-4 rounded-lg bg-amber-500 hover:bg-amber-400 text-black font-bold text-sm uppercase tracking-wider transition-transform active:scale-98 shadow-md"
          >
            <Pause className="w-5 h-5 fill-current" />
            <span>Pause Task</span>
          </button>
        ) : (
          <button
            onClick={() => updateTaskStatus(activeTask.task_id, 'in_progress')}
            className="flex items-center justify-center space-x-2 py-3.5 px-4 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-black font-bold text-sm uppercase tracking-wider transition-transform active:scale-98 shadow-md"
          >
            <Play className="w-5 h-5 fill-current" />
            <span>Start / Resume</span>
          </button>
        )}

        <button
          onClick={() => updateTaskStatus(activeTask.task_id, 'completed')}
          className="flex items-center justify-center space-x-2 py-3.5 px-4 rounded-lg bg-cat-dark hover:bg-cat-hover border border-cat-yellow/50 text-cat-yellow font-bold text-sm uppercase tracking-wider transition-transform active:scale-98 shadow-md"
        >
          <CheckCircle2 className="w-5 h-5" />
          <span>Mark Completed</span>
        </button>
      </div>

      {/* Queued upcoming tasks */}
      {queuedTasks.length > 0 && (
        <div className="mt-5 pt-4 border-t border-cat-border">
          <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider mb-2">
            Next Queued Shift Tasks ({queuedTasks.length})
          </div>
          <div className="space-y-2">
            {queuedTasks.slice(0, 2).map(task => (
              <div key={task.task_id} className="flex items-center justify-between p-2 rounded bg-cat-dark/60 text-xs border border-cat-border/60">
                <div className="flex items-center space-x-2">
                  <span className="font-mono text-cat-yellow font-semibold">{task.task_id}</span>
                  <span className="text-slate-200 capitalize">{task.task_type.replace(/_/g, ' ')}</span>
                </div>
                <span className="text-slate-400 font-mono">{task.quantity} {task.quantity_unit}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
