import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { TrendingUp, Users, Package, ArrowUpRight, ArrowDownRight, Minus, Calendar, ChevronRight } from 'lucide-react';
import api from '../services/api';
import { sfSalesAPI } from '../services/seftaliApi';

const MONTH_NAMES = [
  'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
  'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık',
];

const AllCustomersConsumption = () => {
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedCustomer, setExpandedCustomer] = useState(null);
  const [yoyData, setYoyData] = useState({});
  const [yoyLoading, setYoyLoading] = useState({});

  const today = new Date();
  const currentYear = today.getFullYear();
  const currentMonth = today.getMonth() + 1;

  useEffect(() => {
    fetchCustomersConsumption();
  }, []);

  const fetchCustomersConsumption = async () => {
    try {
      setLoading(true);
      const response = await api.get('/seftali/sales/customers/summary');
      if (response.data.success) {
        setCustomers(response.data.data);
      }
    } catch (error) {
      console.error('Sarfiyat verisi alınamadı:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchYoY = async (customerId) => {
    if (yoyData[customerId]) return;
    setYoyLoading((prev) => ({ ...prev, [customerId]: true }));
    try {
      const response = await sfSalesAPI.getCustomerYoY(customerId, {
        year: currentYear,
        month: currentMonth,
      });
      if (response.data.success) {
        setYoyData((prev) => ({ ...prev, [customerId]: response.data.data }));
      }
    } catch (error) {
      console.error('YoY verisi alınamadı:', error);
    } finally {
      setYoyLoading((prev) => ({ ...prev, [customerId]: false }));
    }
  };

  const toggleExpand = (customerId) => {
    if (expandedCustomer === customerId) {
      setExpandedCustomer(null);
    } else {
      setExpandedCustomer(customerId);
      fetchYoY(customerId);
    }
  };

  const formatRate = (rate) => {
    if (!rate || rate === 0) return '-';
    if (rate >= 1) return `${rate.toFixed(1)}/gün`;
    return `1/${Math.round(1 / rate)} gün`;
  };

  const formatPercent = (pct) => {
    if (pct === 0) return '0%';
    const sign = pct > 0 ? '+' : '';
    return `${sign}${pct.toFixed(1)}%`;
  };

  const trendIcon = (direction) => {
    if (direction === 'growth' || direction === 'new') return <ArrowUpRight className="h-3 w-3" />;
    if (direction === 'decline') return <ArrowDownRight className="h-3 w-3" />;
    return <Minus className="h-3 w-3" />;
  };

  const trendVariant = (direction) => {
    if (direction === 'growth' || direction === 'new') return 'default';
    if (direction === 'decline') return 'destructive';
    return 'secondary';
  };

  const trendLabel = (direction) => {
    switch (direction) {
      case 'growth': return 'Artış';
      case 'decline': return 'Düşüş';
      case 'new': return 'Yeni';
      case 'no_data': return 'Veri yok';
      default: return 'Sabit';
    }
  };

  return (
    <Card data-testid="all-customers-consumption">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="h-5 w-5" />
          Tüm Müşteriler - Sarfiyat Analizi
        </CardTitle>
        <p className="text-sm text-gray-500 mt-1 flex items-center gap-1">
          <Calendar className="h-3 w-3" />
          {MONTH_NAMES[currentMonth - 1]} {currentYear} — Yıldan yıla karşılaştırma için müşteriye tıklayın
        </p>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="text-center py-8 text-gray-500">Yükleniyor...</div>
        ) : customers.length === 0 ? (
          <div className="text-center py-8 text-gray-500">Sarfiyat verisi bulunamadı</div>
        ) : (
          <div className="space-y-4">
            {customers.map((customer, index) => {
              const customerId = customer.customer_id || customer.id;
              const isExpanded = expandedCustomer === customerId;
              const customerYoy = yoyData[customerId];
              const isYoyLoading = yoyLoading[customerId];

              return (
                <div
                  key={customerId || index}
                  className="border rounded-lg p-4"
                  data-testid={`consumption-${customerId}`}
                >
                  <button
                    type="button"
                    className="w-full text-left hover-elevate rounded-md -m-1 p-1"
                    onClick={() => toggleExpand(customerId)}
                    data-testid={`button-toggle-yoy-${customerId}`}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <Users className="h-4 w-4 text-gray-500" />
                        <h3 className="font-semibold">{customer.name || 'Müşteri'}</h3>
                        <ChevronRight
                          className={`h-4 w-4 text-gray-400 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
                        />
                      </div>
                      <Badge variant={customer.trend === 'up' ? 'default' : 'secondary'}>
                        {customer.trend === 'up' ? (
                          <><ArrowUpRight className="h-3 w-3 mr-1" /> Artış</>
                        ) : (
                          <><ArrowDownRight className="h-3 w-3 mr-1" /> Düşüş</>
                        )}
                      </Badge>
                    </div>
                  </button>

                  {customer.top_products && customer.top_products.length > 0 ? (
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                      {customer.top_products.slice(0, 6).map((product, pIndex) => (
                        <div
                          key={pIndex}
                          className="flex items-center gap-2 bg-gray-50 rounded p-2 text-sm"
                        >
                          <Package className="h-3 w-3 text-gray-400" />
                          <span className="truncate flex-1">{product.name}</span>
                          <span className="text-gray-600 font-medium">
                            {formatRate(product.daily_rate)}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500">Henüz sarfiyat verisi yok</p>
                  )}

                  {isExpanded && (
                    <div className="mt-4 border-t pt-4" data-testid={`yoy-panel-${customerId}`}>
                      <div className="flex items-center gap-2 mb-3">
                        <Calendar className="h-4 w-4 text-gray-500" />
                        <h4 className="font-medium text-sm">
                          {MONTH_NAMES[currentMonth - 1]} {currentYear} vs {MONTH_NAMES[currentMonth - 1]} {currentYear - 1}
                        </h4>
                      </div>

                      {isYoyLoading ? (
                        <div className="text-sm text-gray-500 py-3">Yükleniyor...</div>
                      ) : !customerYoy || !customerYoy.items || customerYoy.items.length === 0 ? (
                        <div className="text-sm text-gray-500 py-3">
                          Geçen yıl aynı dönem için karşılaştırma verisi bulunamadı
                        </div>
                      ) : (
                        <div className="space-y-2">
                          {customerYoy.items.slice(0, 8).map((item) => (
                            <div
                              key={item.product_id}
                              className="flex items-center justify-between bg-gray-50 rounded p-2 text-sm"
                              data-testid={`yoy-item-${item.product_id}`}
                            >
                              <span className="truncate flex-1 font-medium">{item.product_name}</span>
                              <div className="flex items-center gap-3 text-xs text-gray-600">
                                <span>{item.previous_year_consumption.toFixed(1)} → {item.current_year_consumption.toFixed(1)}</span>
                                <Badge variant={trendVariant(item.trend_direction)} className="gap-1">
                                  {trendIcon(item.trend_direction)}
                                  {item.trend_direction === 'no_data' || item.trend_direction === 'new'
                                    ? trendLabel(item.trend_direction)
                                    : formatPercent(item.percentage_change)}
                                </Badge>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default AllCustomersConsumption;
