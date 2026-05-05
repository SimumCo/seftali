"""
Rota Optimizasyonu - Nearest Neighbor (En Yakın Komşu) Algoritması
Plasiyer günlük ziyaret sırasını mesafeye göre optimize eder.
"""
from math import radians, cos, sin, asin, sqrt
from typing import List, Dict, Optional


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """İki koordinat arasındaki mesafeyi km cinsinden hesaplar (Haversine formülü)."""
    R = 6371.0
    lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlng / 2) ** 2
    return 2 * R * asin(sqrt(max(0.0, min(1.0, a))))


def nearest_neighbor_optimize(
    customers: List[Dict],
    start_lat: Optional[float] = None,
    start_lng: Optional[float] = None,
) -> List[Dict]:
    """
    Nearest Neighbor algoritmasıyla müşteri ziyaret sırasını optimize eder.

    Args:
        customers: location.lat / location.lng içeren müşteri listesi
        start_lat: Başlangıç noktası enlemi (depo veya plaka konumu)
        start_lng: Başlangıç noktası boylamı

    Returns:
        visit_order alanı güncellenmiş müşteri listesi (koordinatı olmayanlar sona eklenir)
    """
    with_coords = []
    without_coords = []

    for c in customers:
        loc = c.get("location") or {}
        lat = loc.get("lat") or loc.get("latitude")
        lng = loc.get("lng") or loc.get("longitude") or loc.get("lon")
        if lat is not None and lng is not None:
            c = dict(c)
            c["_lat"] = float(lat)
            c["_lng"] = float(lng)
            with_coords.append(c)
        else:
            without_coords.append(c)

    if not with_coords:
        for i, c in enumerate(without_coords):
            c = dict(c)
            c["visit_order"] = i + 1
            without_coords[i] = c
        return without_coords

    # Başlangıç konumu yoksa ilk müşteriyi başlangıç al
    if start_lat is not None and start_lng is not None:
        cur_lat, cur_lng = start_lat, start_lng
        remaining = list(with_coords)
    else:
        first = with_coords[0]
        cur_lat, cur_lng = first["_lat"], first["_lng"]
        remaining = list(with_coords[1:])
        route = [first]
        route[0]["visit_order"] = 1

    route = [] if (start_lat is not None and start_lng is not None) else route
    remaining = list(with_coords) if (start_lat is not None and start_lng is not None) else remaining

    while remaining:
        nearest = min(remaining, key=lambda c: haversine_km(cur_lat, cur_lng, c["_lat"], c["_lng"]))
        remaining.remove(nearest)
        nearest = dict(nearest)
        nearest["visit_order"] = len(route) + 1
        route.append(nearest)
        cur_lat, cur_lng = nearest["_lat"], nearest["_lng"]

    # Koordinatsız müşterileri sona ekle
    for i, c in enumerate(without_coords):
        c = dict(c)
        c["visit_order"] = len(route) + i + 1
        route.append(c)

    # Geçici alanları temizle
    for c in route:
        c.pop("_lat", None)
        c.pop("_lng", None)

    return route


def calculate_total_distance_km(optimized_customers: List[Dict]) -> float:
    """Optimize edilmiş rotanın toplam mesafesini hesaplar."""
    total = 0.0
    prev_lat = prev_lng = None

    for c in optimized_customers:
        loc = c.get("location") or {}
        lat = loc.get("lat") or loc.get("latitude")
        lng = loc.get("lng") or loc.get("longitude") or loc.get("lon")
        if lat is not None and lng is not None:
            if prev_lat is not None:
                total += haversine_km(prev_lat, prev_lng, float(lat), float(lng))
            prev_lat, prev_lng = float(lat), float(lng)

    return round(total, 2)
