$('a#process_input').click(function($e) {
    $e.preventDefault();
    $.getJSON('/display', {
      line: $( "#lineform" ).val(),
      stop: $( "#stopform" ).val(),
      direction: $( "#dirform" ).val()
    }, function(result) {
      console.log(result);
      var $feed = $("div#trainfeed");
      $feed.html('');
      $feed.prepend(result.data);
      });
});

$("#lineform").change(function() {

	var $dropdown = $(this);

	$.getJSON("static/js/stop_dir.json", function(data) {
	
    var key = $dropdown.val();
    console.log(key)
		var vals = [];
							
		switch(key) {
			case '1':
        idx = data.one.ids;
				vals = data.one.names;
				break;
			case '2':
        idx = data.two.ids;
        vals = data.two.names;
        break;
			case '3':
        idx = data.three.ids;
				vals = data.three.names;
				break;
			case '4':
        idx = data.four.ids;
				vals = data.four.names;
        break;
      case '5':
        idx = data.five.ids;
        vals = data.five.names;
        break;
      case '6':
        vals = data.six;
        break;
      case '7':
        vals = data.seven;
        break;
      case 'A':
        vals = data.A;
        break;
      case 'B':
        vals = data.B;
        break;
      case 'C':
        vals = data.C;
        break;
      case 'D':
        vals = data.D;
        break;
      case 'E':
        vals = data.E;
        break;
      case 'F':
        vals = data.F;
        break;
      case 'M':
        vals = data.M;
        break;
      case 'L':
        vals = data.L;
        break;
      case 'J':
        vals = data.J;
        break;
      case 'Z':
        vals = data.Z;
        break;
      case 'N':
        vals = data.N;
        break;
      case 'Q':
        vals = data.Q;
        break;
      case 'R':
        vals = data.R;
        break;
			case 'base':
				vals = ['Please Choose Line'];
		}
		
		var $secondChoice = $("#stopform");
		$secondChoice.empty();
		$.each(vals, function(i, value) {
			$secondChoice.append("<option value=" + idx[i] + ">" + value + "</option>");
		});

	});
});

/////////////////////////////////////////////////////////////////

var svgWidth = 880;
var svgHeight = 680;

// Define the chart's margins as an object
var chartMargin = {
  top: 40,
  right: 40,
  bottom: 40,
  left: 40
};

// Define dimensions of the chart area
var chartWidth = svgWidth - chartMargin.left - chartMargin.right;
var chartHeight = svgHeight - chartMargin.top - chartMargin.bottom;

// Select body, append SVG area to it, and set the dimensions
var svg = d3.select("#delays")
  .append("svg")
  .attr("viewbox", "0 0 100 75")
  .attr("preserveAspectRatio", "none")
  .attr("height", svgHeight)
  .attr("width", svgWidth);

// Append a group to the SVG area and shift ('translate') it to the right and to the bottom
var chartGroup = svg.append("g")
  .attr("transform", `translate(${chartMargin.left}, ${chartMargin.top})`);

d3.json("/api/delays").then(function(delayData) {
  var yScale = d3.scaleBand()
    .domain(delayData.map(d => d.line))
    .range([0, chartHeight])
    .padding(0.1);

  // Create a linear scale for the vertical axis.
  var xScale = d3.scaleLinear()
    .domain([d3.max(delayData, d => (d.count/60)), 0])
    .range([chartWidth, 0]);
  
  var xAxisScale = d3.scaleLinear()
    .domain([d3.min(delayData, d => (d.count/60)), d3.max(delayData, d => (d.count/60))])
    .range([0, chartWidth]);

  var bottomAxis = d3.axisBottom(xAxisScale).ticks(15);
  var leftAxis = d3.axisLeft(yScale).tickSize(0);

  var toolTip = d3.tip()
    .attr("class", "tooltip")
    .offset([0, 10])
    .html(function(d) {
      return (`<strong>${d.line} Line<strong>: ${Math.round(d.count/60)} minutes`);
    }
  );

  svg.call(toolTip);

  chartGroup.selectAll(".bar")
    .data(delayData)
    .enter()
    .append("rect")
    .attr("class", "bar")
    .attr("x", d => xAxisScale(Math.min(0, (d.count/60))))
    .attr("y", d => yScale(d.line))
    .attr("fill", d => d.color)
    .attr("width", d => Math.abs(xAxisScale(d.count/60) - xAxisScale(0)))
    .attr("height", yScale.bandwidth())
    .attr("opacity", ".75")
    .on('mouseover', toolTip.show)
    .on('mouseout', toolTip.hide);
  
  chartGroup.append("g")
    .attr("transform", `translate(${xAxisScale(0)}, 0)`)
    .call(leftAxis);

  chartGroup.append("g")
    .attr("transform", `translate(0, ${chartHeight})`)
    .call(bottomAxis);
});