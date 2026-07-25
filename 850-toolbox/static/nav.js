// Bottom navigation for 850 Toolbox
document.addEventListener('DOMContentLoaded', function(){
    var nav = document.createElement('nav');
    nav.className = 'bn';
    nav.innerHTML =
        '<a href="/" class="bi"><span class="bic">🏠</span><span class="bil">首页</span></a>'+
        '<a href="/k1.html" class="bi"><span class="bic">📊</span><span class="bil">K1</span></a>'+
        '<a href="/sort.html" class="bi"><span class="bic">📋</span><span class="bil">排序</span></a>'+
        '<a href="/shipped.html" class="bi"><span class="bic">🚚</span><span class="bil">出货</span></a>';
    // Highlight current page
    var page = location.pathname.replace('/','').replace('.html','') || 'index';
    nav.querySelectorAll('.bi').forEach(function(a){
        if (a.getAttribute('href').indexOf(page) >= 0) a.classList.add('active');
    });
    document.body.appendChild(nav);
    document.body.style.paddingBottom = '70px';
});
