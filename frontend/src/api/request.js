import axios from "axios"
const request = axios.create({
    //基础地址
    baseURL:'http://127.0.0.1:8000',
    //运行时间
    timeout:5000
})
//暴露出去
// equest.interceptors.request：Axios 的请求拦截器
// ，每次发送请求前都会经过这里。.use()：登记一个处理请求的函数
request.interceptors.request.use((config)=>{
    const token =localStorage.getItem('access_token')
    // getItem浏览器储物柜取出 Token。
    if(token){
        config.headers.Authorization = `Bearer ${token}`
    //config.headers.Authorization 设置标准身份验证请求头。
    // 表示携带的是 Bearer Token。
    }
  
    return config
})
request.interceptors.response.use(
    (response)=>{
        return response
    },
    (error)=>{
        if(error.response?.status === 401){
            localStorage.removeItem('access_token')

            if(window.location.pathname !== '/login'){
                window.location.href='/login'
        }
    }
    return Promise.reject(error)
// interceptors.response：所有后端响应回来后都会经过这里。
// 第一个函数：处理成功响应，必须 return response继续交给页面。
// 第二个函数：处理请求失败。
// error.response?.status：安全读取 HTTP 状态码。
// === 401：判断身份是否失效。
// removeItem()：删除过期或无效的 Token。
// pathname !== '/login'：如果已经在登录页，就不要重复跳转。
// window.location.href：返回登录页。
// Promise.reject(error)：继续把错误交给页面的 catch。
// 删除最后一行后，登录页面可能收不到“用户名或密码错误”。
    }
    
)

export default request