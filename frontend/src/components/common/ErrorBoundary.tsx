import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught component error in CAT Assistant:', error, errorInfo);
    this.setState({ errorInfo });
  }

  private handleReset = () => {
    localStorage.clear();
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-cat-dark flex items-center justify-center p-6 text-white font-mono">
          <div className="bg-cat-panel border-2 border-rose-600 rounded-xl max-w-xl w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center space-x-3 text-rose-400">
              <AlertTriangle className="w-8 h-8" />
              <div>
                <h1 className="text-lg font-bold uppercase tracking-wider">
                  Cab System Diagnostic Failure
                </h1>
                <p className="text-xs text-slate-400">
                  Telemetry runtime error intercepted by safety boundary
                </p>
              </div>
            </div>

            <div className="bg-black/80 p-3 rounded border border-rose-900/60 text-xs text-rose-300 overflow-x-auto">
              {this.state.error?.message || 'Unknown runtime error occurred.'}
            </div>

            <div className="pt-2 flex items-center justify-between">
              <button
                onClick={() => window.location.reload()}
                className="px-4 py-2 rounded bg-cat-yellow text-black font-bold text-xs uppercase flex items-center space-x-1.5"
              >
                <RefreshCw className="w-4 h-4" />
                <span>Reload Application</span>
              </button>

              <button
                onClick={this.handleReset}
                className="px-3 py-2 rounded bg-cat-dark border border-cat-border hover:border-slate-500 text-xs text-slate-400 hover:text-white"
              >
                Reset Local Storage Cache
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
