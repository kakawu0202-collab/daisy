// Lightweight card drag - pure HTML5, no CDN
(function(){
    var dragCard=null, dragIdx=-1;

    function init(){
        var main=document.getElementById('main');
        if(!main)return;
        var cards=main.querySelectorAll(':scope > .card');
        cards.forEach(function(card,i){
            if(card.querySelector('.drg-handle'))return;
            card.style.position='relative';
            var h=document.createElement('span');
            h.className='drg-handle';h.innerHTML='⋮⋮';h.title='拖拽重排';
            h.style.cssText='position:absolute;right:6px;top:4px;cursor:grab;color:var(--muted);font-size:14px;padding:2px 6px;opacity:0.2;z-index:10;';
            card.addEventListener('mouseenter',function(){h.style.opacity='1';});
            card.addEventListener('mouseleave',function(){if(dragCard!==card)h.style.opacity='0.2';});
            card.appendChild(h);
        });

        // Use event delegation on main
        main.addEventListener('dragstart',function(e){
            var card=e.target.closest('.card');if(!card||!card.parentNode||card.parentNode.id!=='main')return;
            dragCard=card;dragIdx=Array.from(main.querySelectorAll(':scope > .card')).indexOf(card);
            card.style.opacity='0.4';
        });
        main.addEventListener('dragend',function(e){
            if(dragCard)dragCard.style.opacity='1';
            dragCard=null;dragIdx=-1;
            main.querySelectorAll('.card').forEach(function(c){c.style.borderTop='';});
        });
        main.addEventListener('dragover',function(e){
            e.preventDefault();
            var card=e.target.closest('.card');if(!card||card===dragCard||!card.parentNode||card.parentNode.id!=='main')return;
            card.style.borderTop='3px solid var(--accent)';
        });
        main.addEventListener('dragleave',function(e){
            var card=e.target.closest('.card');if(card)card.style.borderTop='';
        });
        main.addEventListener('drop',function(e){
            e.preventDefault();
            var card=e.target.closest('.card');
            if(!card||!dragCard||card===dragCard||!card.parentNode||card.parentNode.id!=='main')return;
            card.style.borderTop='';
            var all=Array.from(main.querySelectorAll(':scope > .card'));
            var toIdx=all.indexOf(card);
            if(dragIdx<toIdx)main.insertBefore(dragCard,all[toIdx].nextSibling);
            else main.insertBefore(dragCard,all[toIdx]);
            dragCard.style.opacity='1';dragCard=null;
            saveOrder();
        });

        // Make cards draggable via handle
        cards.forEach(function(card){
            card.setAttribute('draggable','true');
            var h=card.querySelector('.drg-handle');
            if(h){h.addEventListener('mousedown',function(){card.setAttribute('draggable','true');});}
        });
    }

    function saveOrder(){
        var ids=[];document.querySelectorAll('#main > .card h3').forEach(function(h){ids.push(h.textContent.trim().substring(0,30));});
        try{localStorage.setItem('k1_order',JSON.stringify(ids));}catch(e){}
    }

    setTimeout(init,1000);
    window._dragInit=true;
})();
