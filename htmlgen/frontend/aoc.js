google.charts.load('current', {packages: ['corechart', 'line']});
var generated = []

const medal_css = {
    1: {
        // 'background-color': 'gold',
        'background': 'linear-gradient(to bottom right, #ff9988 5%, #ffd700 55%, #ffffff 100%)',
        // 'border': '1px solid #FFCC66',
        // 'box-shadow': '5px 5px #888888',
    },
    2: {
        'background': 'linear-gradient(to bottom right, gray 5%, silver 55%, #ffffff 100%)',
        // 'background-color': 'silver',
        // 'box-shadow': '5px 5px #888888'
    },
    3: {
        'background': 'linear-gradient(to bottom right, GoldenRod 5%, DarkGoldenRod 55%, #ffffff 100%)',
        // 'background-color': 'DarkGoldenRod',
        // 'font-family': 'monospace, sans-serif',
        // // 'border': '4px dotted blue',
        // 'box-shadow': '5px 5px #888888'
    },
}


function fillData(rows) {
    var data = new google.visualization.DataTable();
    // Why is this line required??
    data.addColumn('number', 'X');
    for (var i = 0; i < all_players.length; i++)
    {
        data.addColumn('number', all_players[i]);
    }
    data.addRows(rows);
    return data;
};

function drawChart(elementId, rows, opts) {
    var options = {
        width: $('#tabmenu').width(),
        height: 1000,
        left: 20,
        top: 20,
        hAxis: { title: 'day/star' },
        explorer: {zoomDelta: 1.1},
        // vAxis: { logScale: 'True', title: 'Points behind the leader' },
        ...opts
    };
    var chart = new google.visualization.LineChart(document.getElementById(elementId));
    chart.draw(fillData(rows), options);
}

function stylePosMedals(player, column, medal_data) {
    // Is this a medal-cell?
    const c = medal_data[column]
    if (!c) { return; }

    const medal = c[player];
    if (medal) {
        return medal_css[medal]
    }
}

function zpad(s) {
    return ("00" + s.toString()).slice(-2)
}

function astime(data) {
    var n = parseInt(data, 0);

    if (n == 0) {
        return "Winner";
    }

    if (!(n)) {
        return data;
    }

    var SECSINMIN = 60
    var SECSINHOUR = SECSINMIN * 60
    var HOURSINDAY = 24
    var SECSINDAY = HOURSINDAY * SECSINHOUR

        var days = zpad((n / SECSINDAY) >> 0);
    n = n % SECSINDAY;
    hours = zpad((n / SECSINHOUR) >> 0);
    n = n % SECSINHOUR;
    minutes = zpad((n / SECSINMIN) >> 0)

    seconds = zpad(n % SECSINMIN);

    if (days != "00") {
        return `${days}.${hours}:${minutes}:${seconds}`;
    };
    return `${hours}:${minutes}:${seconds}`
};

function timedelta_to_string(params) {
    const colId = params.column.colId;
    const columns = params.columnApi.columnController.columnDefs;
    for (i = 0; i < columns.length; i++) {
        if (columns[i].field == colId) {
            break;
        }
    }
    if (i < 5) {
        return params.value;
    }
    return astime(params.value);
};


function medalPainter(params) {
    var id = params.column.colId;
    id = id.slice(1).split("_");

    const player = parseInt(params.data.name.split(".")[0].trim());
    const day = parseInt(id[0]);
    const star = parseInt(id[1]);
    const col = day*2 + star;
    return stylePosMedals(player-1, col, medals_best_times);
};

function medalPainter_star2(params) {
    const  id = params.column.colId;
    const day = parseInt(id.slice(1));

    const player = parseInt(params.data.name.split(".")[0].trim());
    return stylePosMedals(player-1, day, medals_star2);
};

function getSortColumn(columns) {
  for (i = 0; i < columns.length; i++) {
    if (columns[i].sortIndex == 0) {
      return i;
    }
  }
}

function sortString(s1, s2) {
  if (s1 == s2) {
    return 0;
  }
  return (s1 > s2) ? 1 : -1;
}

function comparator(valueA, valueB, nodeA, nodeB, isInverted) {
  colIndex = getSortColumn(nodeA.columnApi.getColumnState());

  var k = Object.keys(nodeA.data)[colIndex];

  if (colIndex==0) { // Name
    return sortString(nodeA.data[k], nodeB.data[k]);
  }

  // Map null -> 999 to make those values sort last
  var v1 = (nodeA.data[k] == null) ? 10 * 365 * 24 * 3600 : nodeA.data[k];
  var v2 = (nodeB.data[k] == null) ? 10 * 365 * 24 * 3600 : nodeB.data[k];
  return v1 - v2;
}

function restoreTab() {
  const urlParams = new URLSearchParams(window.location.search);
  var tab = urlParams.get('tab');

  const buttonId = tab ? tab + "_btn" : "btn_Leaderboard";
  tab = tab || "sectionLeaderboard"

  button =  document.getElementById(buttonId);
  if (button) {
    openTab(button, tab, charts)
  }
}

function openTab(target, tabName, config) {
  // Hide all tabs
  const tabs = document.getElementsByClassName("tab");
  for  (const tab of tabs) {
    tab.style.display = "none";
  }

  // Turn off "current tab" indicator
  const buttons = document.getElementsByClassName("tablink");
  for (const button of buttons) {
    button.className = button.className.replace(" w3-red", "");
  }

  // This line doesn't see to do anything
  window.history.pushState({},
    "",
    document.location.origin + document.location.pathname + "?tab=" + tabName);

  // Show requested tab and set red status indicator
  const tab = document.getElementById(tabName);
  if (tab) tab.style.display = "block";
  target.className += " w3-red";
  const datatype = target.attributes.datatype ? target.attributes.datatype.value : undefined
  const datakey = target.attributes.datakey ? target.attributes.datakey.value : undefined
  console.log(datatype)

  if (generated.includes(datakey)) {
    console.log("Using pregenerated widget")
    return;
  };
  generated.push(datakey)

  if (datatype == "table") {
    g = new agGrid.Grid(
      document.querySelector(`#table${datakey}`),
      config[datakey].opts);
  } else if (datatype == "chart") {
    drawChart(
      `chart${datakey}`,
      config[datakey].data,
      config[datakey].opts);
    return;
  } else {
    console.warn("Unknown type: ", datatype);
  }
    if (config[datakey].configFunction) {
      config[datakey].configFunction(datakey, config);
    }
};

function createMenu(config) {
    // var menu = document.getElementById("tabmenu");
    console.log($("#tabmenu"));
    for (chart in charts) {
      // console.log(charts[chart].name)
      $("#tabmenu").append(`
        <button id="btn_${chart}"
                datakey="${chart}"
                datatype="${config[chart].isChart ? 'chart' : 'table'}"
                class="w3-bar-item w3-button tablink"
                onclick="openTab(event.currentTarget, 'section${chart}', charts)">
            ${config[chart].buttonText}
        </button>`);
      if (config[chart].isChart) {
        $("#tables").append(`
        <div id="section${chart}" class="w3-container w3-border tab" style="display:none; height: 100%">
          <h1>${config[chart].header}</h1>
          <p>${config[chart].desc}</p>
          <div class="chart" id="chart${chart}"></div>
        </div>
        `);
      } else {
        $("#tables").append(`
        <div id="section${chart}" class="w3-container w3-border tab" style="display:none; height: 100%">
          <h1>${config[chart].header}</h1>
          <p>${config[chart].desc}</p>
          <div id="table${chart}" style="width: auto;" class="ag-theme-alpine"></div>
        </div>
        `);
      }
    }
  }

window.onload = function() {
    createMenu(charts);
    restoreTab();
}
