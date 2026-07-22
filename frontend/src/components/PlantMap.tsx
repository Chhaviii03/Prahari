import { useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, Polygon, Polyline, CircleMarker, Tooltip, LayersControl, useMap } from 'react-leaflet';
import type { LatLngBoundsExpression, LatLngExpression } from 'leaflet';
import type { ZoneState } from '../types';
import { bandHex } from './ui';

type MapConfig = {
  center: { lat: number; lng: number };
  zoom: number;
  bounds: { south: number; west: number; north: number; east: number };
};

type Worker = { worker_id: string; zone_id: string; lat: number; lng: number; name: string };

type EvacRoute = {
  from_zone: string;
  label?: string;
  route: { lat: number; lng: number }[];
};

const ESRI_SATELLITE =
  'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';

const OSM_TILES = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';

function MapBounds({ bounds }: { bounds: MapConfig['bounds'] }) {
  const map = useMap();
  useEffect(() => {
    const leafletBounds: LatLngBoundsExpression = [
      [bounds.south, bounds.west],
      [bounds.north, bounds.east],
    ];
    map.setMaxBounds(leafletBounds);
    map.fitBounds(leafletBounds, { padding: [24, 24] });
  }, [map, bounds]);
  return null;
}

function zoneStyle(zone: ZoneState) {
  const band =
    zone.band || (zone.crs >= 75 ? 'CRITICAL' : zone.crs >= 40 ? 'ACTIVE' : zone.crs > 0 ? 'WATCH' : 'OK');
  const isStale = zone.data_quality === 'STALE';
  let fill = '#FFF1EC';
  if (!isStale && band === 'CRITICAL') fill = bandHex('CRITICAL');
  else if (!isStale && band === 'ACTIVE') fill = bandHex('ACTIVE');
  else if (!isStale && band === 'WATCH') fill = bandHex('WATCH');
  else if (isStale) fill = '#9CA3AF';
  const opacity = zone.crs > 0 ? Math.min(0.75, 0.2 + zone.crs / 120) : 0.35;
  return { fill, opacity, band };
}

function polygonPath(zone: ZoneState): LatLngExpression[] | null {
  const polygon = zone.geo.polygon as [number, number][] | undefined;
  if (polygon?.length) return polygon.map(([lat, lng]) => [lat, lng]);
  if (zone.geo.lat != null && zone.geo.lng != null) {
    const lat = Number(zone.geo.lat);
    const lng = Number(zone.geo.lng);
    const dLat = 0.0007;
    const dLng = 0.001;
    return [
      [lat + dLat, lng - dLng],
      [lat + dLat, lng + dLng],
      [lat - dLat, lng + dLng],
      [lat - dLat, lng - dLng],
    ];
  }
  return null;
}

export function PlantMap({
  mapConfig,
  zones,
  workers,
  evacRoutes,
}: {
  mapConfig: MapConfig;
  zones: ZoneState[];
  workers: Worker[];
  evacRoutes: EvacRoute[];
}) {
  const center = useMemo(
    () => [mapConfig.center.lat, mapConfig.center.lng] as LatLngExpression,
    [mapConfig],
  );

  return (
    <MapContainer
      center={center}
      zoom={mapConfig.zoom}
      className="h-full w-full rounded-lg z-0"
      style={{ minHeight: 420, background: '#FAF8F8' }}
      scrollWheelZoom
    >
      <MapBounds bounds={mapConfig.bounds} />

      <LayersControl position="topright">
        <LayersControl.BaseLayer checked name="Satellite (Esri)">
          <TileLayer
            url={ESRI_SATELLITE}
            attribution="Tiles &copy; Esri"
            maxZoom={19}
          />
        </LayersControl.BaseLayer>
        <LayersControl.BaseLayer name="OpenStreetMap">
          <TileLayer
            url={OSM_TILES}
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            maxZoom={19}
          />
        </LayersControl.BaseLayer>
      </LayersControl>

      {evacRoutes.map((route, idx) =>
        route.route.length >= 2 ? (
          <Polyline
            key={`evac-${idx}`}
            positions={route.route.map((p) => [p.lat, p.lng] as LatLngExpression)}
            pathOptions={{ color: '#DC2626', weight: 3, dashArray: '8 6' }}
          />
        ) : null,
      )}

      {zones.map((zone) => {
        const path = polygonPath(zone);
        if (!path) return null;
        const { fill, opacity, band } = zoneStyle(zone);
        return (
          <Polygon
            key={zone.zone_id}
            positions={path}
            pathOptions={{
              color: zone.crs >= 40 ? fill : '#E5E7EB',
              weight: zone.crs >= 40 ? 2 : 1,
              fillColor: fill,
              fillOpacity: opacity,
            }}
          >
            <Tooltip direction="top" sticky>
              <div className="text-xs">
                <strong>{zone.zone_id}</strong> — {zone.name}
                <br />
                CRS {zone.crs.toFixed(0)} · {band}
                {zone.occupancy > 0 && (
                  <>
                    <br />
                    Workers: {zone.occupancy}
                  </>
                )}
              </div>
            </Tooltip>
          </Polygon>
        );
      })}

      {workers.map((w) => (
        <CircleMarker
          key={w.worker_id}
          center={[w.lat, w.lng]}
          radius={6}
          pathOptions={{ color: '#FFFFFF', weight: 1.5, fillColor: '#F5A892', fillOpacity: 1 }}
        >
          <Tooltip>{w.name}</Tooltip>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
