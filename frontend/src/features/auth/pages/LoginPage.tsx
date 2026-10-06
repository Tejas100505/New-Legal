/**
 * LoginPage — premium glassmorphism authentication with Sign In & Sign Up for Attorneys.
 */

import { useState, type FormEvent } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Scale, Mail, Lock, User, Building, Award, ArrowRight, AlertCircle, CheckCircle2 } from 'lucide-react';
import { useAuthStore } from '@/features/auth/store';
import { cn } from '@/lib/utils';

export function LoginPage() {
  const { login, register, isLoading } = useAuthStore();
  const [mode, setMode] = useState<'signin' | 'signup'>('signin');

  // Form states
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [firm, setFirm] = useState('');
  const [barNumber, setBarNumber] = useState('');

  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  const switchMode = (newMode: 'signin' | 'signup') => {
    setMode(newMode);
    setError('');
    setSuccessMsg('');
  };

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    setSuccessMsg('');

    const trimmedEmail = email.trim();

    if (mode === 'signin') {
      if (!trimmedEmail || !password) {
        setError('Please enter your email and password.');
        return;
      }
      try {
        await login(trimmedEmail, password);
      } catch (err: any) {
        setError(err?.message || 'Invalid credentials. Please try again.');
      }
    } else {
      // Sign Up validation
      const trimmedName = fullName.trim();
      if (!trimmedName) {
        setError('Please enter your full legal name.');
        return;
      }
      if (!trimmedEmail || !trimmedEmail.includes('@') || !trimmedEmail.includes('.')) {
        setError('Please provide a valid email address.');
        return;
      }
      if (password.length < 8) {
        setError('Password must be at least 8 characters long.');
        return;
      }
      if (!/[A-Z]/.test(password)) {
        setError('Password must contain at least one uppercase letter.');
        return;
      }
      if (!/[a-z]/.test(password)) {
        setError('Password must contain at least one lowercase letter.');
        return;
      }
      if (!/[0-9]/.test(password)) {
        setError('Password must contain at least one digit.');
        return;
      }
      if (!/[^A-Za-z0-9]/.test(password)) {
        setError('Password must contain at least one special character.');
        return;
      }
      if (password !== confirmPassword) {
        setError('Passwords do not match. Please verify.');
        return;
      }

      try {
        await register({
          email: trimmedEmail,
          password,
          fullName: trimmedName,
          firm: firm.trim() || undefined,
          barNumber: barNumber.trim() || undefined,
        });
        setSuccessMsg('Account created successfully! Logging you in...');
      } catch (err: any) {
        setError(err?.message || 'Registration failed. Please verify your details.');
      }
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: 'easeOut' }}
      className="w-full max-w-md mx-auto"
    >
      {/* Logo */}
      <div className="flex flex-col items-center mb-6">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
          className="h-14 w-14 rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-2xl shadow-indigo-500/30 mb-3"
        >
          <Scale className="h-7 w-7 text-white" />
        </motion.div>
        <h1 className="text-2xl font-bold text-slate-100">
          <span className="gradient-text">E-Discovery</span> AI
        </h1>
        <p className="text-xs text-slate-400 mt-1">Enterprise Legal Intelligence Platform</p>
      </div>

      {/* Card */}
      <div
        className={cn(
          'rounded-2xl p-6 sm:p-8',
          'bg-slate-900/70 backdrop-blur-2xl',
          'border border-slate-800/80',
          'shadow-2xl shadow-black/40'
        )}
      >
        {/* Header and Toggle Tabs */}
        <div className="flex items-center justify-between mb-6 pb-4 border-b border-slate-800/60">
          <div>
            <h2 className="text-lg font-semibold text-slate-100">
              {mode === 'signin' ? 'Attorney Sign In' : 'Create Attorney Account'}
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              {mode === 'signin'
                ? 'Enter your credentials to access case files'
                : 'Self-register for case review & e-discovery'}
            </p>
          </div>
          <div className="flex bg-slate-950/60 p-1 rounded-lg border border-slate-800">
            <button
              type="button"
              id="signin-tab-btn"
              onClick={() => switchMode('signin')}
              className={cn(
                'px-3 py-1 text-xs font-semibold rounded transition-all',
                mode === 'signin'
                  ? 'bg-indigo-600 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200'
              )}
            >
              Sign In
            </button>
            <button
              type="button"
              id="signup-tab-btn"
              onClick={() => switchMode('signup')}
              className={cn(
                'px-3 py-1 text-xs font-semibold rounded transition-all',
                mode === 'signup'
                  ? 'bg-indigo-600 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200'
              )}
            >
              Sign Up
            </button>
          </div>
        </div>

        {/* Alerts */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="flex items-start gap-2.5 px-3.5 py-3 mb-4 rounded-lg bg-rose-500/10 border border-rose-500/20 text-xs text-rose-400"
            >
              <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </motion.div>
          )}
          {successMsg && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="flex items-center gap-2.5 px-3.5 py-3 mb-4 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-400"
            >
              <CheckCircle2 className="h-4 w-4 shrink-0" />
              <span>{successMsg}</span>
            </motion.div>
          )}
        </AnimatePresence>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Sign Up Exclusive Fields */}
          {mode === 'signup' && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="space-y-3.5"
            >
              <div className="space-y-1">
                <label className="block text-xs font-medium text-slate-300">
                  Full Legal Name <span className="text-rose-400">*</span>
                </label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="e.g. Sarah Jenkins, Esq."
                    className="w-full pl-9 pr-3 py-2 rounded-lg bg-slate-950/80 border border-slate-700/80 text-slate-100 text-xs placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2.5">
                <div className="space-y-1">
                  <label className="block text-xs font-medium text-slate-300">Law Firm / Org</label>
                  <div className="relative">
                    <Building className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
                    <input
                      type="text"
                      value={firm}
                      onChange={(e) => setFirm(e.target.value)}
                      placeholder="Apex Legal LLP"
                      className="w-full pl-9 pr-3 py-2 rounded-lg bg-slate-950/80 border border-slate-700/80 text-slate-100 text-xs placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
                    />
                  </div>
                </div>
                <div className="space-y-1">
                  <label className="block text-xs font-medium text-slate-300">State Bar ID</label>
                  <div className="relative">
                    <Award className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
                    <input
                      type="text"
                      value={barNumber}
                      onChange={(e) => setBarNumber(e.target.value)}
                      placeholder="BAR-12345"
                      className="w-full pl-9 pr-3 py-2 rounded-lg bg-slate-950/80 border border-slate-700/80 text-slate-100 text-xs placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
                    />
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {/* Email */}
          <div className="space-y-1">
            <label className="block text-xs font-medium text-slate-300">
              Email Address <span className="text-rose-400">*</span>
            </label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="attorney@firm.com"
                className="w-full pl-9 pr-3 py-2 rounded-lg bg-slate-950/80 border border-slate-700/80 text-slate-100 text-xs placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
                required
                autoComplete="email"
              />
            </div>
          </div>

          {/* Password */}
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <label className="block text-xs font-medium text-slate-300">
                Password <span className="text-rose-400">*</span>
              </label>
              {mode === 'signup' && (
                <span className="text-[10px] text-slate-500">Min 8 chars, uppercase, lowercase, number, symbol</span>
              )}
            </div>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-9 pr-3 py-2 rounded-lg bg-slate-950/80 border border-slate-700/80 text-slate-100 text-xs placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
                required
                minLength={8}
                autoComplete={mode === 'signin' ? 'current-password' : 'new-password'}
              />
            </div>
          </div>

          {/* Confirm Password (Sign Up only) */}
          {mode === 'signup' && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="space-y-1"
            >
              <label className="block text-xs font-medium text-slate-300">
                Confirm Password <span className="text-rose-400">*</span>
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-9 pr-3 py-2 rounded-lg bg-slate-950/80 border border-slate-700/80 text-slate-100 text-xs placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
                  required
                  minLength={8}
                  autoComplete="new-password"
                />
              </div>
            </motion.div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isLoading}
            className={cn(
              'w-full flex items-center justify-center gap-2 py-2.5 rounded-xl mt-2',
              'bg-gradient-to-r from-indigo-500 to-violet-500 text-white font-semibold text-xs',
              'shadow-lg shadow-indigo-500/20 hover:shadow-indigo-500/40',
              'hover:brightness-110 active:brightness-95',
              'transition-all duration-200',
              'disabled:opacity-50 disabled:cursor-not-allowed'
            )}
          >
            {isLoading ? (
              <div className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <>
                {mode === 'signin' ? 'Sign In to Review Portal' : 'Register Account'}
                <ArrowRight className="h-3.5 w-3.5" />
              </>
            )}
          </button>
        </form>

        {/* Demo Credentials Quick Fill (available in Sign In mode) */}
        {mode === 'signin' && (
          <div className="mt-5 pt-4 border-t border-slate-800/50">
            <button
              type="button"
              disabled={isLoading}
              onClick={async () => {
                setEmail('user@example.com');
                setPassword('Password123!');
                try {
                  await login('user@example.com', 'Password123!');
                } catch (err: any) {
                  setError(err?.message || 'Authentication failed');
                }
              }}
              className="w-full py-2 px-3 rounded-xl bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/30 text-xs font-semibold text-indigo-300 hover:text-white transition-all flex items-center justify-center gap-2 cursor-pointer shadow-sm hover:shadow-indigo-500/10"
            >
              <Scale className="h-4 w-4 text-indigo-400" />
              <span>1-Click Sign In: Lead Counsel (<code>user@example.com</code>)</span>
            </button>
          </div>
        )}

        {/* Mode Toggle Footer Prompt */}
        <div className="mt-4 text-center">
          {mode === 'signin' ? (
            <p className="text-xs text-slate-400">
              New legal counsel?{' '}
              <button
                type="button"
                onClick={() => switchMode('signup')}
                className="text-indigo-400 hover:text-indigo-300 font-semibold underline underline-offset-2 transition-colors"
              >
                Create an account
              </button>
            </p>
          ) : (
            <p className="text-xs text-slate-400">
              Already have an account?{' '}
              <button
                type="button"
                onClick={() => switchMode('signin')}
                className="text-indigo-400 hover:text-indigo-300 font-semibold underline underline-offset-2 transition-colors"
              >
                Sign in
              </button>
            </p>
          )}
        </div>
      </div>

      {/* Footer */}
      <p className="text-center text-[11px] text-slate-600 mt-4">
        E-Discovery & Legal Review Intelligence — Enterprise Grade RBAC
      </p>
    </motion.div>
  );
}
