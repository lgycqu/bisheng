import { BookOpenIcon } from '@/components/bs-icons/bookOpen';
import { GithubIcon } from '@/components/bs-icons/github';
import { useContext, useEffect, useRef, useState } from "react";
import { useTranslation } from 'react-i18next';
import json from "../../../package.json";
import { Button } from "../../components/bs-ui/button";
import { Input } from "../../components/bs-ui/input";
// import { alertContext } from "../contexts/alertContext";
import { useToast } from "@/components/bs-ui/toast/use-toast";
import { useLocation, useNavigate } from 'react-router-dom';
import { getCaptchaApi, loginApi, registerApi } from "../../controllers/API/user";
import { captureAndAlertRequestErrorHoc } from "../../controllers/request";
import LoginBridge from './loginBridge';
import { PWD_RULE, handleEncrypt, handleLdapEncrypt } from './utils';
import { locationContext } from '@/contexts/locationContext';
import { ldapLoginApi } from '@/controllers/API/pro';

export const LoginPage = () => {
    // const { setErrorData, setSuccessData } = useContext(alertContext);
    const { t, i18n } = useTranslation();
    const { message, toast } = useToast()
    const navigate = useNavigate()
    const { appConfig } = useContext(locationContext)
    const isLoading = false

    const mailRef = useRef(null)
    const pwdRef = useRef(null)
    const agenPwdRef = useRef(null)

    // login or register
    const [showLogin, setShowLogin] = useState(true)

    useLoginError()

    // captcha
    const captchaRef = useRef(null)
    const [captchaData, setCaptchaData] = useState({ captcha_key: '', user_capthca: false, captcha: '' });

    useEffect(() => {
        fetchCaptchaData();
    }, []);

    const fetchCaptchaData = () => {
        getCaptchaApi().then(setCaptchaData)
    };

    const [isLDAP, setIsLDAP] = useState(false)
    const handleLogin = async () => {
        const error = []
        const [mail, pwd] = [mailRef.current.value, pwdRef.current.value]
        if (!mail) error.push(t('login.pleaseEnterAccount'))
        if (!pwd) error.push(t('login.pleaseEnterPassword'))
        if (captchaData.user_capthca && !captchaRef.current.value) error.push(t('login.pleaseEnterCaptcha'))
        if (error.length) return message({
            title: `${t('prompt')}`,
            variant: 'warning',
            description: error
        })
        // if (error.length) return setErrorData({
        //     title: `${t('prompt')}:`,
        //     list: error,
        // });

        const encryptPwd = isLDAP ? await handleLdapEncrypt(pwd) : await handleEncrypt(pwd)
        captureAndAlertRequestErrorHoc(
            (isLDAP
                ? ldapLoginApi(mail, encryptPwd)
                : loginApi(mail, encryptPwd, captchaData.captcha_key, captchaRef.current?.value)
            ).then((res: any) => {
                window.self === window.top ? localStorage.removeItem('ws_token') : localStorage.setItem('ws_token', res.access_token)
                localStorage.setItem('isLogin', '1')
                const pathname = localStorage.getItem('LOGIN_PATHNAME')
                if (pathname) {
                    // After the login session expires, redirect back to the login page. After successful login, redirect back to the page before login. 
                    localStorage.removeItem('LOGIN_PATHNAME')
                    location.href = pathname
                } else {
                    const path = import.meta.env.DEV ? '/admin' : '/workspace/'
                    const rootUrl = `${location.origin}${__APP_ENV__.BASE_URL}${path}`
                    location.href = `${__APP_ENV__.BASE_URL}${location.pathname}` === '/' ? rootUrl : location.href
                }
            }), (error) => {
                if (error.indexOf('过期') !== -1) { // 有时间改为 code 判断
                    localStorage.setItem('account', mail)
                    navigate('/reset', { state: { noback: true } })
                }
            })

        fetchCaptchaData()
    }

    const handleRegister = async () => {
        const error = []
        const [mail, pwd, apwd] = [mailRef.current.value, pwdRef.current.value, agenPwdRef.current.value]
        if (!mail) {
            error.push(t('login.pleaseEnterAccount'))
        }
        if (mail.length < 3) {
            error.push(t('login.accountTooShort'))
        }
        if (!/.{8,}/.test(pwd)) {
            error.push(t('login.passwordTooShort'))
        }
        if (!PWD_RULE.test(pwd)) {
            error.push(t('login.passwordError'))
        }
        if (pwd !== apwd) {
            error.push(t('login.passwordMismatch'))
        }
        if (captchaData.user_capthca && !captchaRef.current.value) {
            error.push(t('login.pleaseEnterCaptcha'))
        }
        if (error.length) {
            return message({
                title: `${t('prompt')}`,
                variant: 'warning',
                description: error
            })
        }
        const encryptPwd = await handleEncrypt(pwd)
        captureAndAlertRequestErrorHoc(registerApi(mail, encryptPwd, captchaData.captcha_key, captchaRef.current?.value).then(res => {
            // setSuccessData({ title: t('login.registrationSuccess') })
            message({
                title: `${t('prompt')}`,
                variant: 'success',
                description: [t('login.registrationSuccess')]
            })
            pwdRef.current.value = ''
            setShowLogin(true)
        }))

        fetchCaptchaData()
    }

    return <div className='min-h-screen w-full flex items-center justify-center bg-background-dark'>
        <div className='w-full max-w-[420px] mx-4 p-8 bg-background-login rounded-xl shadow-lg'>
            {/* Logo 和标语 */}
            <div className='text-center mb-8'>
                {/* 自定义 LINRI Logo */}
                <span className="text-[#3b5998] text-3xl font-bold tracking-wide">LINRI</span>
                <p className='text-[14px] text-tx-color mt-4'>{t('login.slogen')}</p>
            </div>

            {/* 表单 */}
            <div className="space-y-4">
                <Input
                    id="email"
                    className='h-[48px] dark:bg-login-input'
                    ref={mailRef}
                    placeholder={t('login.account')}
                    type="email"
                    autoCapitalize="none"
                    autoComplete="email"
                    autoCorrect="off"
                />
                <Input
                    id="pwd"
                    className='h-[48px] dark:bg-login-input'
                    ref={pwdRef}
                    placeholder={t('login.password')}
                    type="password"
                    onKeyDown={e => e.key === 'Enter' && showLogin && handleLogin()}
                />
                {!showLogin && (
                    <Input
                        id="confirmPwd"
                        className='h-[48px] dark:bg-login-input'
                        ref={agenPwdRef}
                        placeholder={t('login.confirmPassword')}
                        type="password"
                    />
                )}
                {captchaData.user_capthca && (
                    <div className="flex items-center gap-3">
                        <Input
                            type="text"
                            ref={captchaRef}
                            placeholder={t('login.pleaseEnterCaptcha')}
                            className="h-[48px] flex-1 dark:bg-login-input"
                        />
                        <img
                            src={'data:image/jpg;base64,' + captchaData.captcha}
                            alt="captcha"
                            onClick={fetchCaptchaData}
                            className="h-[48px] w-[100px] cursor-pointer rounded border border-gray-200 hover:opacity-80"
                        />
                    </div>
                )}

                {showLogin ? (
                    <>
                        {!isLDAP && appConfig.register && (
                            <div className="text-center">
                                <a href="javascript:;" className="text-blue-500 text-sm hover:underline" onClick={() => setShowLogin(false)}>
                                    {t('login.noAccountRegister')}
                                </a>
                            </div>
                        )}
                        <Button className='w-full h-[48px] mt-4 dark:bg-button' disabled={isLoading} onClick={handleLogin}>
                            {t('login.loginButton')}
                        </Button>
                    </>
                ) : (
                    <>
                        <div className="text-center">
                            <a href="javascript:;" className="text-blue-500 text-sm hover:underline" onClick={() => setShowLogin(true)}>
                                {t('login.haveAccountLogin')}
                            </a>
                        </div>
                        <Button className='w-full h-[48px] mt-4 dark:bg-button' disabled={isLoading} onClick={handleRegister}>
                            {t('login.registerButton')}
                        </Button>
                    </>
                )}

                {appConfig.isPro && <LoginBridge onHasLdap={setIsLDAP} />}
            </div>

            {/* 底部信息 */}
            <div className="mt-8 pt-6 border-t border-gray-100 dark:border-gray-700 flex items-center justify-center gap-4">
                <span className="text-sm text-gray-400">v{json.version}</span>
                {!appConfig.noFace && (
                    <div className='flex gap-2'>
                        <a href={"https://github.com/dataelement/bisheng"} target="_blank">
                            <GithubIcon className="h-[36px] w-[36px] p-2 border rounded-lg hover:bg-[#1b1f23] hover:text-white cursor-pointer" />
                        </a>
                        <a href={"https://m7a7tqsztt.feishu.cn/wiki/ZxW6wZyAJicX4WkG0NqcWsbynde"} target="_blank">
                            <BookOpenIcon className="h-[36px] w-[36px] p-2 border rounded-lg hover:bg-[#0055e3] hover:text-white cursor-pointer" />
                        </a>
                    </div>
                )}
            </div>
        </div>
    </div>
};




export const useLoginError = () => {
    const location = useLocation();
    const { toast } = useToast();
    const { t } = useTranslation();

    useEffect(() => {
        const queryParams = new URLSearchParams(location.search);
        const code = queryParams.get('status_code')
        if (code) {
            toast({
                variant: 'error',
                description: t('errors.' + code)
            })
        }
    }, [location])
}