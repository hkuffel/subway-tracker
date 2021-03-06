$(document).ready(function() {
  var socket = io.connect('http://' + document.domain + ':' + location.port);
  socket.on('my event', function(msg) {
    d3.json("/api/delays").then(function(delayData) {
      update(delayData)
    });
  });
});

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
        idx = data.six.ids;
        vals = data.six.names;
        break;
      case '7':
        idx = data.seven.ids;
        vals = data.seven.names;
        break;
      case 'A':
        idx = data.A.ids;
        vals = data.A.names;
        break;
      case 'B':
        idx = data.B.ids;
        vals = data.B.names;
        break;
      case 'C':
        idx = data.C.ids;
        vals = data.C.names;
        break;
      case 'D':
        idx = data.D.ids;
        vals = data.D.names;
        break;
      case 'E':
        idx = data.E.ids;
        vals = data.E.names;
        break;
      case 'F':
        idx = data.F.ids;
        vals = data.F.names;
        break;
      case 'M':
        idx = data.M.ids;
        vals = data.M.names;
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
  .attr("viewbox", "0 0 0 0")
  .attr("justify-content", "center")
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
    .attr("id", d => d.line)
    .attr("x", d => xAxisScale(Math.min(0, (d.count/60))))
    .attr("y", d => yScale(d.line))
    .attr("fill", d => d.color)
    .attr("width", d => Math.abs(xAxisScale(d.count/60) - xAxisScale(0)))
    .attr("height", yScale.bandwidth())
    .attr("opacity", ".75")
    .on('mouseover', toolTip.show)
    .on('mouseout', toolTip.hide);
  
  chartGroup.append("g")
    .attr("class", "xaxis")
    .attr("transform", `translate(${xAxisScale(0)}, 0)`)
    .call(leftAxis);

  chartGroup.append("g")
    .attr("class", "bottomaxis")
    .attr("transform", `translate(0, ${chartHeight})`)
    .call(bottomAxis);
});

function update(delayData) {
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
  chartGroup.selectAll(".bar")
  .data(delayData)
  .transition().duration(500)
  .attr("x", d => xAxisScale(Math.min(0, (d.count/60))))
  .attr("y", d => yScale(d.line))
  .attr("width", d => Math.abs(xAxisScale(d.count/60) - xAxisScale(0)))
  .attr("height", yScale.bandwidth())

  chartGroup.selectAll(".xaxis")
  .transition().duration(250)
  .attr("transform", `translate(${xAxisScale(0)}, 0)`)
  .call(leftAxis)

  chartGroup.selectAll(".bottomaxis")
  .transition().duration(250)
  .attr("transform", `translate(0, ${chartHeight})`)
  .call(bottomAxis);
  console.log('this is where I would be updating.')
}