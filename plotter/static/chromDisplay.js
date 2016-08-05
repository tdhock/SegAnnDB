// We assume another script defines e.g.
//     <script type="text/javascript">
// var profiles = new profilePlot(rowList);
//     </script>

function profilePlot(rowList) {
    console.log(rowList);
    var plot = d3.select("#plot");
    var table = plot.append("table");
    
    this.updateModel = function(modelData) {
        if (modelData.hasOwnProperty("updates")) {
            for (var i = 0; i < modelData.updates.length; i++) {
                d = modelData.updates[i];
                cd = CHROM_DISPLAYS[d.profile_id][d.chromosome];
                if (cd) {
                    cd.updateModel(d.update);
                }
            }
        }
    }
    
    CHROM_DISPLAYS = {};
    var profiles = [];
    var chromosomes = [];
    for (var i = 0; i < rowList.length; i++) {
        var prof_info = rowList[i];
        var profile_id = prof_info[0].profile;
        profiles[i] = profile_id;
        if (prof_info.length > 1 && i == 0) {
            var tr = table.append("tr");
            if (rowList.length > 1) {
                tr.append("td");
            }
            tr.selectAll("td.chromLabel")
            .data(prof_info)
            .enter().append("td")
            .classed("chromLabel", 1)
            .append("a")
            .attr("href", function(d) {
                return d.chr + '/';
            })
            .text(function(d) {
                return d.chr;
            })
            ;
        }
        var tr = table.append("tr")
        .classed("chromDisplay", 1)
        ;
        if (rowList.length > 1) {
            tr.append("td")
            .classed("chromRow", 1)
            .append("a")
            .attr("href", "/profile/" + profile_id + "/")
            .text(profile_id)
            ;
        }
        var tds = tr.selectAll("td.chromDisplay")
        .data(prof_info)
        .enter().append("td")
        .classed("chromDisplay chromRow", 1)
        ;
        var svgs = tds.append("svg")
        .attr("id", function(d) {
            return "pro" + d.profile + "chrom" + d.chr;
        })
        .attr("width", function(d) {
            return d.width_px
        })
        .attr("height", function(d) {
            return d.height_px
        })
        // load background scatterplot.
        .style("background-image", function(d) {
            // scatterurl was modified in order to make it work with the new fiile
            // keeping scheme
            var fileName = "";
            if (d.zoom == undefined || d.index_suffix == undefined)
            {
              d.zoom = "";
              d.index_suffix = "";
              fileName = d.file;
            }
            else
              fileName = d.profile + "_chr" + d.chr + "_" + d.zoom + d.index_suffix + ".png";
            var scatter_url = "/secret/" + d.profile + "/" + d.chr + "/" + fileName;
            return "url('" + scatter_url + "')";
        })
        ;
        CHROM_DISPLAYS[profile_id] = {};
        for (var j = 0; j < prof_info.length; j++) {
            var chr = prof_info[j].chr;
            chromosomes[j] = chr;
            var svg = d3.select("#pro" + profile_id + "chrom" + chr);
            var cd = new chromDisplay(svg,prof_info[j],this);
            CHROM_DISPLAYS[profile_id][chr] = cd;
        }
    }
    d3.json("/initial/" + profiles.join(",") + "/" + chromosomes.join(',') + "/", 
    this.updateModel);
}

var MIN_REGION_WIDTH = 5;

var ANNOTATIONS = {
    "copies": {
        "colors": {
            "loss": "#93b9ff",
            "normal": '#f6f4bf',
            "gain": "#ff7d7d",
            "unlabeled": "#0adb0a",
            "multilabeled": "black",
            "deletion": "#3564ba",
            "amplification": "#d02a2a",
        },
        "order": ["normal", "loss", "gain", "deletion", "amplification"],
    },
    "breakpoints": {
        "colors": {
            "1breakpoint": "#ff7d7d",
            "0breakpoints": '#f6f4bf',
            //	    ">0breakpoints":"#a445ee",
        },
        "order": ["1breakpoint", "0breakpoints"],
    },
};
//shortcuts
var ANNOTATION_COLOR = ANNOTATIONS["copies"]["colors"];
var ANNOTATION_ORDER = ANNOTATIONS["copies"]["order"];
var NEXT_ANNOTATION = make_next_dict(ANNOTATION_ORDER);

function annotation_color(d) {
    return ANNOTATION_COLOR[d.annotation];
}


function make_next_dict(order) {
    var next = {};
    for (var i = 1; i < order.length; i++) {
        next[order[i - 1]] = order[i];
    }
    next[order[order.length - 1]] = order[0];
    return next;
}

function getRegion(x1, x2) {
    var left, right;
    if (x1 < x2) {
        left = x1;
        right = x2;
    } else {
        right = x1;
        left = x2;
    }
    return {
        "x": left,
        "width": right - left
    };
}

function chromDisplay(svg, meta, plotter) {
    var chromosome = meta["chr"];
    var width = meta["width_px"];
    var height = meta["height_px"];
    var profile_id = meta["profile"];

    // modified the range : width -> meta["original_width"] 
    // as have hard set the width px to 1250px
    // below is working fix for both plot_profile.pt and new.pt to get right 
    // x values.
    if (width == 1250)
      if (meta["original_width"]) // this second if is for accomodating profile_old
        width = meta["original_width"];

    var x = d3.scale.linear()
    .domain([1, meta["width_bases"]])
    .range([0, width]);
    
    var y = d3.scale.linear()
    .domain([meta["logratio_min"], meta["logratio_max"]])
    .range([height, 0]);
    
    this.copiesTrack = new annotationTrack(this,0,height / 2 + 1,"copies");
    this.breakpointsTrack = new annotationTrack(this,
    height / 2,height / 2,"breakpoints");
    
    function annotationTrack(chromD, trackY, trackHeight, trackType) {
        var trackAnns = ANNOTATIONS[trackType];
        var trackColors = trackAnns["colors"];
        var trackOrder = trackAnns["order"];
        var trackNext = make_next_dict(trackOrder);
        var button_class = trackType + "Button";
        var textH = 20;
        var button_y = trackY + textH;
        var directlabel_y = trackY + trackHeight - 3;
        var trackFirst = trackOrder[0];
        drag_origin = null ;
        var disable_new = function() {
            background.call(doNothing);
        }
        var enable_new = function() {
            background.call(newRegion);
        }
        this.disable_new = disable_new;
        this.enable_new = enable_new;
        var deleteAnnotation = function() {
            var rect = svg.select("#" + trackType + "NEW");
            rect.remove();
            var buttons = svg.selectAll("." + button_class);
            buttons.remove();
            var directlabel = svg.selectAll("." + button_class + "directlabel");
            directlabel.remove();
            enable_new();
        }
        var saveAnnotation = function() {
            var buttons = svg.selectAll("." + button_class);
            buttons.remove();
            var rect = svg.select("#" + trackType + "NEW");
            var w = parseInt(rect.attr("width"));
            var min_px = parseInt(rect.attr("x"));
            var min = parseInt(x.invert(min_px));
            var max = parseInt(x.invert(min_px + w));
            var waiting = svg.append("text")
            .attr("x", min_px + w / 2)
            .attr("y", button_y)
            .text("Waiting for response from server...")
            .style("font-weight", "bold")
            .style("text-anchor", "middle")
            .attr("class", button_class)
            ;
            var directlabel = svg.selectAll("." + button_class + "directlabel")
            .attr("class", trackType)
            ;
            var ann = directlabel.text();
            rect.on("click", null );
            var url = "/add_region/" + profile_id + "/" + chromosome + "/" + 
            trackType + "/" + ann + "/" + min + "/" + max + "/";
            d3.json(url, function(response) {
                if (response) {
                    rect.data([response.region]);
                    rectActions(rect);
                    directlabel
                    .attr("id", trackType + response.region.id + "label");
                    plotter.updateModel(response);
                } else {
                    rect.remove();
                    directlabel.remove();
                }
                waiting.remove();
                enable_new();
            });
        }
        var doNothing = d3.behavior.drag();
        var newRegion = d3.behavior.drag()
        .on("dragstart", function(d) {
            drag_origin = d3.mouse(this)[0];
            var rect = svg.insert("rect", "line")
            .attr("id", trackType + "NEW")
            .attr("y", trackY)
            .attr("x", drag_origin)
            .attr("width", MIN_REGION_WIDTH)
            .attr("height", trackHeight)
            .style("fill", trackColors[trackFirst])
            .style("opacity", 0.7)
            ;
        })
        .on("drag", function(d) {
            var r = getRegion(d3.event.x, drag_origin);
            svg.select("#" + trackType + "NEW")
            .attr("x", r["x"])
            .attr("width", r["width"])
            ;
        })
        .on("dragend", function(d) {
            drag_origin = null ;
            // convert to genome units
            var rect = svg.select("#" + trackType + "NEW");
            var rectL = parseInt(rect.attr("x"));
            var rectR = rectL + parseInt(rect.attr("width"));
            // do not allow regions outside the point range
            var cropL = chromD.cropPixelToPlot(rectL);
            var cropR = chromD.cropPixelToPlot(rectR);
            if (cropL == cropR) {
                //both outside range
                rect.remove();
                return;
            }
            // abort if too small.
            if (cropR - cropL < MIN_REGION_WIDTH) {
                rect.remove()
                return;
            }
            rect.attr("x", cropL)
            .attr("width", cropR - cropL)
            ;
            rect.append("svg:title")
            .text("click to change annotation")
            ;
            var mid_px = (cropL + cropR) / 2;
            var x_space = 2;
            var buttons = [
            {
                "sign": -1,
                "name": "Delete",
                "anchor": "end",
                "fun": deleteAnnotation
            }, 
            {
                "sign": 1,
                "name": "Save",
                "anchor": "start",
                "fun": saveAnnotation
            }, 
            ];
            var text = svg.selectAll("text." + button_class)
            .data(buttons)
            .enter()
            .append("text")
            .attr("x", function(d) {
                return mid_px + d["sign"] * x_space;
            })
            .attr("y", button_y)
            .text(function(d) {
                return d["name"];
            })
            .style("text-anchor", function(d) {
                return d["anchor"];
            })
            .style("font-size", textH + "px")
            .attr("class", button_class)
            ;
            var both = text[0];
            var text_w_px = [];
            for (var i = 0; i < both.length; i++) {
                text_w_px[i] = both[i].getComputedTextLength();
            }
            var rectData = [
            {
                "x": mid_px - text_w_px[0] - x_space * 2,
                "fun": deleteAnnotation,
                "width": text_w_px[0] + x_space * 2
            }, 
            {
                "x": mid_px,
                "fun": saveAnnotation,
                "width": text_w_px[1] + x_space * 2
            }, 
            ];
            var textback = svg.selectAll("rect." + button_class)
            .data(rectData)
            .enter()
            .append("rect")
            .attr("class", button_class)
            .on("mouseover", function(d) {
                d3.select(this).style("stroke", "black");
            })
            .on("mouseout", function(d) {
                d3.select(this).style("stroke", "");
            })
            .style("fill", "transparent")
            .attr("x", function(d) {
                return d["x"];
            })
            .attr("width", function(d) {
                return d["width"];
            })
            .attr("y", trackY)
            .attr("height", textH + 2)
            .on("click", function(d) {
                d["fun"]();
            })
            ;
            var directlabel = svg.append("text")
            .attr("x", mid_px)
            .attr("y", directlabel_y)
            .text(trackFirst)
            .style("text-anchor", "middle")
            .style("font-weight", "bold")
            .attr("class", button_class + "directlabel")
            ;
            rect
            .on("click", function(d) {
                var newann = trackNext[directlabel.text()];
                rect.style("fill", trackColors[newann]);
                directlabel.text(newann);
            })
            ;
            
            disable_new();
            return;
        })
        ;
        
        var background = svg.append("rect")
        .attr("y", trackY)
        .attr("width", width)
        .attr("height", trackHeight)
        .attr("fill", "transparent")
        ;
        background.append("svg:title")
        .text("Drag to annotate " + trackType)
        ;
        
        function rectActions(rects) {
            rects
            .attr("class", trackType)
            .attr("id", function(d) {
                return trackType + d.id;
            })
            .style("opacity", 0.7)
            .on("click", function(d) {
                if (d3.event.shiftKey) {
                    //zoom to ucsc.
                    var chr = "chr" + chromosome;
                    var pos = "position=" + chr + ":" + d.min + "-" + d.max;
                    var base = "http://genome.ucsc.edu/cgi-bin/hgTracks";
                    var db = "db=" + meta["db"];
                    var url = base + "?" + pos + "&" + db;
                    window.open(url);
                    //http://genome.ucsc.edu/cgi-bin/hgTracks?position=chr3:48520879-57961549
                } else {
                    // normal click, delete the annotation.
                    //need to have bound at least .id and .annotation
                    var rect = d3.select(this);
                    var directlabel = d3.select("#" + trackType + d.id + "label");
                    var url = "/delete_region/" + 
                    profile_id + "/" + chromosome + "/" + 
                    trackType + "/" + d.id + "/";
                    d3.json(url, function(response) {
                        if (response) {
                            rect.remove();
                            directlabel.remove();
                            plotter.updateModel(response);
                        }
                    });
                }
            })
            .on("mouseover", function(d) {
                d3.select(this).style("stroke", "black");
            })
            .on("mouseout", function(d) {
                d3.select(this).style("stroke", "");
            })
            ;
            rects.text("")
            .append("svg:title")
            .text("Click to delete, shift-click to zoom to UCSC")
            ;
        }
        
        this.updateRegions = function(regions) {
            var rects = svg.selectAll("rect." + trackType)
            .data(regions)
            .enter().insert("rect", "line")
            .style("fill", function(d) {
                return trackColors[d.annotation];
            })
            .attr("x", function(d) {
                return x(d.min);
            })
            .attr("width", function(d) {
                return x(d.max) - x(d.min);
            })
            .attr("y", 0)
            .attr("height", trackHeight)
            .attr("y", trackY)
            ;
            var directlabels = svg.selectAll("text." + trackType)
            .data(regions)
            .enter().append("text")
            .text(function(d) {
                return d.annotation;
            })
            .attr("x", function(d) {
                return (x(d.min) + x(d.max)) / 2;
            })
            .attr("y", directlabel_y)
            .style("text-anchor", "middle")
            .style("font-weight", "bold")
            .attr("id", function(d) {
                return trackType + d.id + "label";
            })
            ;
            rectActions(rects);
        }
    }
    
    this.updateModel = function(response) {
        
        // the response contains ids of everything onscreen that has
        // changed.
        if (response.segments) {
            // draw guide lines first.
            var guides = svg.selectAll("line.guide")
            .data([{
                "logratio": 0
            }, {
                "logratio": -1
            }, {
                "logratio": 1
            }])
            ;
            // changing the x2 value to 1250, as each image will only be 1250
            // pixels long
            var guideActions = function(selection) {
                var url = window.location.href;
                var res = url.indexOf("profile_old");

                if (res == -1)
                    width = 1250;
                
                selection.attr("x1", 0)
                .attr("x2", width)
                .attr("y1", function(d) {
                    return y(d.logratio);
                })
                .attr("y2", function(d) {
                    return y(d.logratio);
                })
                .classed("guide", 1)
                .style("stroke-width", function(d) {
                    if (d.logratio)
                        return "1px";
                    else
                        return "3px";
                })
                ;
            }
            guideActions(guides.enter().append("line"));
            guideActions(guides);
            var segmentation = svg.selectAll("line.segmentation")
            .data(response.segments);
            segmentation.enter().append("line");
            segmentation
            .attr("x1", function(d) {
                return x(d.min - 0.5);
            })
            .attr("x2", function(d) {
                return x(d.max);
            })
            .attr("y1", function(d) {
                return y(d.logratio);
            })
            .attr("y2", function(d) {
                return y(d.logratio);
            })
            .style("stroke", annotation_color)
            .classed("segmentation", 1)
            ;
            segmentation.exit().remove();
            // some segmentation was returned,
            // so if there are no breakpoints
            // that means we need to create an empty list
            // so that d3 will erase the previous breakpoints!
            if (response.segments.length == 1) {
                response.breakpoints = [];
            }
            this.breakpointsTrack.enable_new();
            this.copiesTrack.enable_new();
            // TODO: limit annotations.
            this.XLIM_PX = [1, width - 1];
        }
        if (response.breakpoints) {
            var breakpoints = svg.selectAll("line.breakpoint")
            .data(response.breakpoints);
            breakpoints.enter().append("line");
            breakpoints.exit().remove();
            breakpoints
            .attr("x1", function(d) {
                return x(d.position + 0.5);
            })
            .attr("x2", function(d) {
                return x(d.position + 0.5);
            })
            .attr("y1", function(d) {
                return 0;
            })
            .attr("y2", function(d) {
                return height;
            })
            .classed("breakpoint", 1)
            .text("")
            .style("stroke", function(d) {
                if (response.segannot) {
                    return "purple";
                } else {
                    return "#0adb0a";
                }
            })
            .append("svg:title")
            .text(function(d) {
                if (response.segannot) {
                    return "purple=SegAnnot";
                } else {
                    return "green=PrunedDP";
                }
            })
            ;
        }
        
        this.cropPixelToPlot = function(px) {
            return Math.min(Math.max(px, this.XLIM_PX[0]), 
            this.XLIM_PX[1]);
        }
        if (response.breakpoints_regions && this.breakpointsTrack) {
            this.breakpointsTrack.updateRegions(response.breakpoints_regions);
        }
        if (response.copies_regions && this.copiesTrack) {
            this.copiesTrack.updateRegions(response.copies_regions);
        }
    }
}
