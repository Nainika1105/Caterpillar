import React, { createContext, useContext, useEffect, useState } from 'react';
import { Role, Operator, Machine } from '../types';
import { api } from '../services/api';

const EMPTY_OPERATOR: Operator = { operator_id: '', name: 'Loading operator', experience_years: 0, home_site_id: '', shift: '', certifications: [] };
const EMPTY_MACHINE: Machine = { machine_id: '', machine_class: 'excavator', powertrain: 'diesel', reference_model: '', site_id: '', engine_hours_at_start: 0, commission_year: 0 };

interface AuthContextType {
  role: Role;
  setRole: (role: Role) => void;
  activeOperator: Operator;
  setActiveOperator: (op: Operator) => void;
  activeMachine: Machine;
  setActiveMachine: (machine: Machine) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [role, setRoleState] = useState<Role>(() => {
    return (localStorage.getItem('cat_user_role') as Role) || 'operator';
  });

  const [activeOperator, setActiveOperatorState] = useState<Operator>(EMPTY_OPERATOR);
  const [activeMachine, setActiveMachineState] = useState<Machine>(EMPTY_MACHINE);

  useEffect(() => {
    Promise.all([api.getOperators(), api.getMachines()]).then(([operators, machines]) => {
      const operator = operators.find(item => item.operator_id === 'OP1002') || operators[0];
      const machine = machines.find(item => item.machine_id === 'EXC002') || machines[0];
      if (operator) setActiveOperatorState(operator);
      if (machine) setActiveMachineState(machine);
    }).catch(() => undefined);
  }, []);

  const setRole = (newRole: Role) => {
    setRoleState(newRole);
    localStorage.setItem('cat_user_role', newRole);
  };

  const setActiveOperator = (op: Operator) => {
    setActiveOperatorState(op);
    // Find matching or assigned machine
    api.getMachines().then(machines => {
      const machine = machines.find(item => item.primary_operator_id === op.operator_id);
      if (machine) setActiveMachineState(machine);
    }).catch(() => undefined);
  };

  const setActiveMachine = (mach: Machine) => {
    setActiveMachineState(mach);
  };

  return (
    <AuthContext.Provider value={{
      role,
      setRole,
      activeOperator,
      setActiveOperator,
      activeMachine,
      setActiveMachine,
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
};
