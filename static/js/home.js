


function getToken(){$.ajax({
      type: 'GET',
        dataType:"jsonp",
      url: 'http://0.0.0.0:8000/token/',
      headers:{
      },
      success: function (data, status, xhr) {
        console.log('data: ', data);
      }
    })}
$(document).on('click','bot-login-btn', getToken());