"""
��ԴȨ�޹���·��ģ��: �ṩ�û��������Դ֮��Ȩ�޹�ϵ�Ĺ�����
[Ǩ���Ž�] - ���ļ���Ǩ���� app/api/frontend/security/permissions.py
"""

from fastapi import APIRouter
import logging

# �����µ�APIģ��
from app.api.frontend.security.permissions import router as new_router

# ����·��
router = APIRouter()
logger = logging.getLogger(__name__)

# ��¼Ǩ�ƾ���
logger.warning("ʹ�������õ�app/api/resource_permission.py�����ļ���Ǩ����app/api/frontend/security/permissions.py")

# ����������ת�����µ�·�ɴ�����
for route in new_router.routes:
    router.routes.append(route)
