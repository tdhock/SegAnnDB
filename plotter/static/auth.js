/***************
 *
 * auth.js
 *
 * This script handles the client side part of login and logut functions
 *
 * Abhishek Shrivastava <x.abhishek.flyhigh> GSoC '16
 ***************/

// check if user is logged in or not
// on basis of that show appropriate buttons
var user = getCookie("authtkt");
var divElem = $("#auth");

if (user != "") 
{
    var button = "<button id='signout' onclick='bye()'>Log Out</button>";
    divElem.append(button);
}
else
{
  // okay the user is not logged in 
  // render the login button
  var button = "<a href='/auth/signin_redirect' id='signin'><button>Login</button></a>";
  divElem.append(button);
}

// function to erase cookies
// courtsey StackOverflow :)
// - http://stackoverflow.com/questions/179355/clearing-all-cookies-with-javascript
function eraseCookieFromAllPaths(name) {
    // This function will attempt to remove a cookie from all paths.
    var pathBits = location.pathname.split('/');
    var pathCurrent = ' path=';

    // do a simple pathless delete first.
    document.cookie = name + '=; expires=Thu, 01-Jan-1970 00:00:01 GMT;';

    for (var i = 0; i < pathBits.length; i++) {
        pathCurrent += ((pathCurrent.substr(-1) != '/') ? '/' : '') + pathBits[i];
        document.cookie = name + '=; expires=Thu, 01-Jan-1970 00:00:01 GMT;' + pathCurrent + ';';
    }
}

// function to logout the user
function bye()
{
  eraseCookieFromAllPaths("authtkt");

  //now we need to refresh the page as well.
  location.reload();
}

// function to get a cookie from cookie storage
function getCookie(cname) 
{
  var name = cname + "=";
  var ca = document.cookie.split(';');
  for(var i = 0; i < ca.length; i++)
  {
      var c = ca[i];
      while (c.charAt(0) == ' ')
      {
          c = c.substring(1);
      }
      if (c.indexOf(name) == 0) 
      {
          return c.substring(name.length, c.length);
      }
  }
  return "";
}

