import { useContext, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { userContext } from '../contexts/userContext';

/**
 * 管理后台落地页
 * 根据用户权限自动重定向到第一个可访问的页面
 */
export default function AdminLanding() {
    const navigate = useNavigate();
    const { user } = useContext(userContext);

    useEffect(() => {
        if (!user) return;

        const isAdmin = ['admin', 'group_admin'].includes(user.role);
        const hasMenu = (menu: string) => user.web_menu.includes(menu) || user.role === 'admin';

        // 按优先级检查权限并重定向
        if (hasMenu('build')) {
            navigate('/build/apps', { replace: true });
        } else if (hasMenu('knowledge')) {
            navigate('/filelib', { replace: true });
        } else if (hasMenu('model')) {
            navigate('/model/management', { replace: true });
        } else if (hasMenu('evaluation')) {
            navigate('/evaluation', { replace: true });
        } else if (isAdmin) {
            navigate('/log', { replace: true });
        } else {
            // 标注页面对所有用户开放
            navigate('/label', { replace: true });
        }
    }, [user, navigate]);

    return (
        <div className="flex items-center justify-center h-screen">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
    );
}
