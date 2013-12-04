/**
 * 
 */
$(document).ready(function() {

        // JQuery code to be added in here.
    $('#likes').click(function(){
        var catid;
        catid = $(this).attr("data-catid");
         $.get('/rango/like_category/', {category_id: catid}, function(data){
                   $('#like_count').html(data);
                   $('#likes').hide();
               });
    });
    
    $('#suggestion').keyup(function(){
        var query;
        query = $(this).val();
        $.get('/rango/suggest_category/', {suggestion: query}, function(data){
         $('#cats').html(data);
        });
    });
    
    $('.btn-mini').click(function(){
        
    	var catid = $(this).attr("data-catid");
    	var title = $(this).attr("data-title");
    	var url = $(this).attr("data-url");
    	var spanid = "#" + $(this).attr("data-id");
    	var buttonid = "#_" + spanid;
        var status = false;

        $.get('/rango/auto_add_page/', {"category_id": catid, "url": url, "title": title}, function(data, success){
            console.log('success = ' + success + '[' + typeof(success) +'][' + success.length + ']');
            if (success == "success" )
            {
                status = true;
                console.log('1. hide\n'); 
                $(spanid).hide();
                $(buttonid).hide();
                $(spanid).remove();
                $(buttonid).remove();
            }
        });
        console.log("status=  " + status)
    });

});