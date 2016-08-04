// Script to handle the creation of interactive overviews
function drawJumps(rowData)
{
  // some Global Variables
  var STANDARD_WIDTH = 1250;
  var IPAD_WIDTH = 20000;
  var CHROME_UBUNTU_MAX = 1000000;
  var CHROME_WINDOWS_MAX = 300000;

  // dict for getting the right zoomlevels;
  var zooms = {
    standard : STANDARD_WIDTH,
    ipad : IPAD_WIDTH,
    chrome_windows : CHROME_WINDOWS_MAX,
    chrome_ubuntu : CHROME_UBUNTU_MAX
  };

  // these variables will be same for all profiles, so taking them from just
  // one profile.
  var zoomLevel = rowData[0][0]["zoom"];
  var widthBase = rowData[0][0]["width_bases"];


  // get the number of links to generate
  var numLinks = zooms[zoomLevel] / STANDARD_WIDTH;

  var divElem = $("#random_jumps");

  // proceed if only numlinks is greater than one, else we will have errors
  if (numLinks > 0)
  {
    var overviewDiv = $("#overview");

    // get the width of each link
    var linkWidth = 1250 / numLinks;

    // we need to calculate the width dynamically.
    var linkStyle = "width:" + linkWidth + "px;"

    for (var i = 1; i <= numLinks; i++)
    {
      // lets create the links
      // calculate the href value
      var hrefVal = "?width="+zoomLevel + "&index=" + i;

      // create a linear scale for making the title
      var x = d3.scale.linear()
              .domain([1, widthBase])
              .range([0, zooms[zoomLevel]]);

      // title values we use inverted range to get the values
      var basePixel = (i - 1) * 1250;
      var xstartBP = x.invert(basePixel);
      var xendBP = x.invert(basePixel + 1250);

      // generate the title string
      var title = xstartBP + "-" + xendBP;

      // make the string of link
      var link = "<a class='overviewLink' style="+linkStyle+" href="+hrefVal+" title="+title+"></a>";

      // append the links to overview
      overviewDiv.append(link);

      // calculate the base pair range of each idex using reverse
      // this is the bottom list of links
      divElem.append("<a class='jumpLink' href="+hrefVal+ " title="+title+">"+i+"</a>");

      // add the breaks after every 35 values to the bottom list of links
      if (i % 35 == 0)
        divElem.append("<br>");
    }
  }
}
