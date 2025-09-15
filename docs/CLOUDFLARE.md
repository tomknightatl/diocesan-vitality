We have configured a Cloudflare tunnel using the Cloudflare WebUI with the following Public Hostnames:

Frontend
diocesan-vitality.diocesevitality.org | http://frontend-service.default.svc.cluster.local:80
# 2025-09-14: This one is not yet working, because Cloudflare is overwriting the DNS record we create for it:
diocesanvitality.org      | http://frontend-service.default.svc.cluster.local:80

Backend:
api.diocesevitality.org   | http://backend-service.diocesan-vitality.svc.cluster.local:8000
api.diocesanvitality.org  | http://backend-service.diocesan-vitality.svc.cluster.local:8000