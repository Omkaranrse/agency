import React from 'react';
import { describe, it, expect } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { EmployeeRoster } from '@/components/office/employee-roster';
import { WorkstationsPanel } from '@/components/office/workstations-panel';
import { TasksOverviewTable } from '@/components/office/tasks-overview-table';
import { EmployeeDetailDrawer } from '@/components/office/employee-detail-drawer';
import type {
  OfficeEmployeeState,
  WorkstationState,
  TaskRecord,
} from '@/features/office/types';

const mockEmployees: OfficeEmployeeState[] = [
  {
    role: 'manager',
    name: 'Alex Morgan',
    title: 'AI Agency Manager',
    avatar: 'manager',
    workstation: 'manager_desk',
    status: 'working',
    active_task_id: 'task-mgr',
    current_activity: 'Supervising multi-agent execution pipeline.',
    last_active_at: '2026-10-21T12:00:00Z',
    is_logical_role: false,
    completed_steps_count: 1,
  },
  {
    role: 'pm',
    name: 'Sofia Chen',
    title: 'Project Manager',
    avatar: 'pm',
    workstation: 'planning_desk',
    status: 'completed',
    active_task_id: null,
    current_activity: 'Specification and architecture completed.',
    last_active_at: '2026-10-21T12:05:00Z',
    is_logical_role: false,
    completed_steps_count: 1,
  },
  {
    role: 'designer',
    name: 'Liam Vance',
    title: 'UI/UX Designer',
    avatar: 'designer',
    workstation: 'design_station',
    status: 'completed',
    active_task_id: null,
    current_activity: 'Design tokens synthesized.',
    last_active_at: '2026-10-21T12:10:00Z',
    is_logical_role: false,
    completed_steps_count: 1,
  },
  {
    role: 'reviewer',
    name: 'Operator / Reviewer',
    title: 'Client Review Gate',
    avatar: 'reviewer',
    workstation: 'review_area',
    status: 'waiting_approval',
    active_task_id: 'task-rev',
    current_activity: 'Awaiting operator review on preview.',
    last_active_at: '2026-10-21T12:15:00Z',
    is_logical_role: true,
    completed_steps_count: 0,
  },
  {
    role: 'builder',
    name: 'Marcus Brody',
    title: 'Full-Stack Builder',
    avatar: 'builder',
    workstation: 'development_station',
    status: 'idle',
    active_task_id: null,
    current_activity: 'Standby for stage invocation.',
    last_active_at: null,
    is_logical_role: false,
    completed_steps_count: 0,
  },
  {
    role: 'qa',
    name: 'Elena Rostova',
    title: 'QA Engineer',
    avatar: 'qa',
    workstation: 'qa_station',
    status: 'idle',
    active_task_id: null,
    current_activity: null,
    last_active_at: null,
    is_logical_role: false,
    completed_steps_count: 0,
  },
  {
    role: 'devops',
    name: 'DevOps Engineer',
    title: 'Infrastructure & Edge Deploy',
    avatar: 'devops',
    workstation: 'operations_station',
    status: 'idle',
    active_task_id: null,
    current_activity: null,
    last_active_at: null,
    is_logical_role: false,
    completed_steps_count: 0,
  },
];

const mockWorkstations: WorkstationState[] = [
  {
    id: 'manager_desk',
    name: 'Manager Desk',
    description: 'Executive oversight and workflow tracking.',
    assigned_role: 'manager',
    active_task_id: 'task-mgr',
    queued_task_ids: [],
    status: 'active',
  },
  {
    id: 'planning_desk',
    name: 'Planning Desk',
    description: 'Requirements breakdown and technical specifications.',
    assigned_role: 'pm',
    active_task_id: null,
    queued_task_ids: [],
    status: 'completed',
  },
  {
    id: 'design_station',
    name: 'Design Station',
    description: 'Design tokens, color palettes, and layout synthesis.',
    assigned_role: 'designer',
    active_task_id: null,
    queued_task_ids: [],
    status: 'completed',
  },
  {
    id: 'review_area',
    name: 'Review Area',
    description: 'Interactive prototype inspection and human approval.',
    assigned_role: 'reviewer',
    active_task_id: 'task-rev',
    queued_task_ids: [],
    status: 'waiting_approval',
  },
  {
    id: 'development_station',
    name: 'Development Station',
    description: 'Component synthesis and Astro template assembly.',
    assigned_role: 'builder',
    active_task_id: null,
    queued_task_ids: ['task-bld'],
    status: 'idle',
  },
  {
    id: 'qa_station',
    name: 'QA Station',
    description: 'Automated headless testing, accessibility, and SEO.',
    assigned_role: 'qa',
    active_task_id: null,
    queued_task_ids: ['task-qa'],
    status: 'idle',
  },
  {
    id: 'operations_station',
    name: 'Operations Station',
    description: 'VCS commits and edge production deployment.',
    assigned_role: 'devops',
    active_task_id: null,
    queued_task_ids: ['task-dep'],
    status: 'idle',
  },
];

const mockTasks: TaskRecord[] = [
  {
    id: 'task-planning',
    run_id: 'run-test-1',
    agent_role: 'pm',
    task_type: 'planning',
    title: 'Specification & Requirements Analysis',
    status: 'completed',
    started_at: '2026-10-21T12:00:00Z',
    updated_at: '2026-10-21T12:05:00Z',
    completed_at: '2026-10-21T12:05:00Z',
    progress_details: 'Specification completed.',
    blocker: null,
    attempt_number: 1,
    related_artifact_ids: ['spec.json'],
  },
  {
    id: 'task-rev',
    run_id: 'run-test-1',
    agent_role: 'reviewer',
    task_type: 'approval',
    title: 'Prototype Review & Operator Approval',
    status: 'waiting_approval',
    started_at: '2026-10-21T12:10:00Z',
    updated_at: '2026-10-21T12:15:00Z',
    completed_at: null,
    progress_details: 'Awaiting operator review on preview: https://preview.run/1',
    blocker: null,
    attempt_number: 1,
    related_artifact_ids: [],
  },
];

describe('EmployeeRoster Component', () => {
  it('renders all team members with names and titles', () => {
    const html = renderToStaticMarkup(
      <EmployeeRoster
        employees={mockEmployees}
        selectedRole={null}
        onSelectEmployee={() => {}}
      />
    );

    expect(html).toContain('Alex Morgan');
    expect(html).toContain('Sofia Chen');
    expect(html).toContain('Liam Vance');
    expect(html).toContain('Marcus Brody');
    expect(html).toContain('Elena Rostova');
    expect(html).toContain('Operator / Reviewer');
    expect(html).toContain('DevOps Engineer');

    // Shows 7 members count
    expect(html).toContain('7 members');

    // Identifies Gate / Logical role badge
    expect(html).toContain('Gate');

    // Status badges
    expect(html).toContain('Working');
    expect(html).toContain('Awaiting Sign-off');
    expect(html).toContain('Completed');
    expect(html).toContain('Idle / Standby');
  });

  it('highlights selected employee with active ring styling', () => {
    const html = renderToStaticMarkup(
      <EmployeeRoster
        employees={mockEmployees}
        selectedRole="reviewer"
        onSelectEmployee={() => {}}
      />
    );

    expect(html).toContain('aria-pressed="true"');
    expect(html).toContain('border-accent');
  });
});

describe('WorkstationsPanel Component', () => {
  it('renders all 7 workstation zones with descriptions and badges', () => {
    const html = renderToStaticMarkup(
      <WorkstationsPanel
        workstations={mockWorkstations}
        tasks={mockTasks}
        onSelectRole={() => {}}
      />
    );

    expect(html).toContain('Manager Desk');
    expect(html).toContain('Planning Desk');
    expect(html).toContain('Design Station');
    expect(html).toContain('Review Area');
    expect(html).toContain('Development Station');
    expect(html).toContain('QA Station');
    expect(html).toContain('Operations Station');

    // Status badges
    expect(html).toContain('Active Station');
    expect(html).toContain('Awaiting Sign-off');
    expect(html).toContain('Completed');
    expect(html).toContain('Idle Standby');

    // Shows active operation in review area
    expect(html).toContain('Prototype Review &amp; Operator Approval');
  });
});

describe('TasksOverviewTable Component', () => {
  it('renders task list with status badges and timestamps', () => {
    const html = renderToStaticMarkup(
      <TasksOverviewTable
        tasks={mockTasks}
        onSelectRole={() => {}}
      />
    );

    expect(html).toContain('Specification &amp; Requirements Analysis');
    expect(html).toContain('Prototype Review &amp; Operator Approval');
    expect(html).toContain('Completed');
    expect(html).toContain('Awaiting Approval');
    expect(html).toContain('1 files');
  });

  it('renders empty fallback when tasks array is empty', () => {
    const html = renderToStaticMarkup(
      <TasksOverviewTable
        tasks={[]}
        onSelectRole={() => {}}
      />
    );

    expect(html).toContain('No tasks recorded for this run.');
  });
});

describe('EmployeeDetailDrawer Component', () => {
  it('renders detailed employee state, task information, and artifacts', () => {
    const emp = mockEmployees[3]; // Reviewer
    const task = mockTasks[1];

    const html = renderToStaticMarkup(
      <EmployeeDetailDrawer
        employee={emp}
        task={task}
        runId="run-test-1"
        onClose={() => {}}
      />
    );

    expect(html).toContain('Operator / Reviewer');
    expect(html).toContain('Client Review Gate');
    expect(html).toContain('Awaiting Sign-off');
    expect(html).toContain('Human Gate / Operator');
    expect(html).toContain('review area');
    expect(html).toContain('Prototype Review &amp; Operator Approval');
    expect(html).toContain('Run ID: run-test-1');
  });
});
