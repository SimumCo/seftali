import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { LockKeyhole, UserRound } from 'lucide-react';

import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '../components/ui/card';

export default function CustomerLoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { user, loginCustomer } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (user?.role === 'customer') {
      navigate(user.must_change_password ? '/customer/change-password' : '/customer', { replace: true });
    }
  }, [navigate, user]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    const result = await loginCustomer(username, password);
    if (result.success) {
      const mustChange = result.data?.must_change_password;
      toast.success('Giriş başarılı');
      navigate(mustChange ? '/customer/change-password' : '/customer', { replace: true });
    } else {
      toast.error(result.error || 'Giriş başarısız');
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-10">
      <div className="mx-auto flex min-h-[80vh] max-w-md items-center justify-center">
        <Card className="w-full rounded-[28px] border-slate-200 shadow-[0_24px_60px_-35px_rgba(15,23,42,0.35)]" data-testid="customer-login-card">
          <CardHeader className="space-y-4 text-left">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-orange-50 text-orange-600">
              <UserRound className="h-7 w-7" />
            </div>
            <div className="space-y-1">
              <CardTitle className="text-3xl font-bold tracking-tight">Müşteri Girişi</CardTitle>
              <CardDescription className="text-sm text-slate-500">
                Vergi numarası veya TC kimlik numaranız ile giriş yapın.
              </CardDescription>
            </div>
          </CardHeader>

          <form onSubmit={handleSubmit}>
            <CardContent className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="customer-username">Kullanıcı Adı</Label>
                <Input
                  id="customer-username"
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  placeholder="TC / Vergi No"
                  className="h-12 rounded-2xl"
                  data-testid="customer-login-username-input"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="customer-password">Şifre</Label>
                <Input
                  id="customer-password"
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="Şifrenizi girin"
                  className="h-12 rounded-2xl"
                  data-testid="customer-login-password-input"
                  required
                />
              </div>
              <div className="rounded-2xl bg-slate-50 px-4 py-3 text-xs text-slate-500" data-testid="customer-login-helper-text">
                İlk girişte şifre değiştirmeniz istenebilir.
              </div>
            </CardContent>
            <CardFooter className="flex-col gap-3">
              <Button
                type="submit"
                className="h-12 w-full rounded-2xl bg-orange-500 text-base font-semibold hover:bg-orange-600"
                disabled={loading}
                data-testid="customer-login-submit-button"
              >
                {loading ? 'Giriş yapılıyor...' : 'Giriş Yap'}
              </Button>
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <LockKeyhole className="h-3.5 w-3.5" />
                Yalnızca yetkili müşteri hesapları giriş yapabilir.
              </div>
            </CardFooter>
          </form>
        </Card>
      </div>
    </div>
  );
}
