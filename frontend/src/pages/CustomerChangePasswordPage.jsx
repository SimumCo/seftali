import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { KeyRound, ShieldCheck } from 'lucide-react';

import { customerAuthAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '../components/ui/card';

export default function CustomerChangePasswordPage() {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { user, markCustomerPasswordChanged } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const customerToken = localStorage.getItem('customer_token');
    if (!customerToken) {
      navigate('/customer-login', { replace: true });
      return;
    }
    if (user?.role === 'customer' && user.must_change_password === false) {
      navigate('/customer', { replace: true });
    }
  }, [navigate, user]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    try {
      const response = await customerAuthAPI.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      if (response.data?.success) {
        markCustomerPasswordChanged();
        toast.success('Şifre başarıyla güncellendi');
        navigate('/customer', { replace: true });
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Şifre değiştirilemedi');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-10">
      <div className="mx-auto flex min-h-[80vh] max-w-md items-center justify-center">
        <Card className="w-full rounded-[28px] border-slate-200 shadow-[0_24px_60px_-35px_rgba(15,23,42,0.35)]" data-testid="customer-change-password-card">
          <CardHeader className="space-y-4 text-left">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-orange-50 text-orange-600">
              <KeyRound className="h-7 w-7" />
            </div>
            <div className="space-y-1">
              <CardTitle className="text-3xl font-bold tracking-tight">Şifre Değiştir</CardTitle>
              <CardDescription className="text-sm text-slate-500">
                Sistemi kullanmaya devam etmek için şifrenizi güncelleyin.
              </CardDescription>
            </div>
          </CardHeader>

          <form onSubmit={handleSubmit}>
            <CardContent className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="current-password">Mevcut Şifre</Label>
                <Input
                  id="current-password"
                  type="password"
                  value={currentPassword}
                  onChange={(event) => setCurrentPassword(event.target.value)}
                  placeholder="Mevcut şifreniz"
                  className="h-12 rounded-2xl"
                  data-testid="customer-change-password-current-input"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="new-password">Yeni Şifre</Label>
                <Input
                  id="new-password"
                  type="password"
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                  placeholder="Yeni şifreniz"
                  className="h-12 rounded-2xl"
                  data-testid="customer-change-password-new-input"
                  required
                />
              </div>
              <div className="rounded-2xl bg-slate-50 px-4 py-3 text-xs text-slate-500" data-testid="customer-change-password-helper-text">
                Minimum 8 karakter, en az 1 harf ve 1 rakam kullanın.
              </div>
            </CardContent>
            <CardFooter className="flex-col gap-3">
              <Button
                type="submit"
                className="h-12 w-full rounded-2xl bg-orange-500 text-base font-semibold hover:bg-orange-600"
                disabled={loading}
                data-testid="customer-change-password-submit-button"
              >
                {loading ? 'Güncelleniyor...' : 'Şifreyi Güncelle'}
              </Button>
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <ShieldCheck className="h-3.5 w-3.5" />
                Şifreniz güncellendikten sonra müşteri ekranına yönlendirileceksiniz.
              </div>
            </CardFooter>
          </form>
        </Card>
      </div>
    </div>
  );
}
