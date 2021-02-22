google.charts.load('current', {packages: ['corechart', 'line']});
var generated = []
var medals_best_times, medals_star2, all_players;

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

const urlRoot = "https://scoreboard-html.s3.us-east-2.amazonaws.com";
var year, uuid;

function maxDays() {
  const now = new Date();
  // getMonth returns 0..11
  if (now.getMonth() == 11 && now.getFullYear() == parseInt(year)) {
    return now.getDate();
  }
  return 25;
}

function makeUrl(s) {
  if (!s) {
    throw Error("Cannot generate Url from empty string-token.")
  }
  const url = `${urlRoot}/${year}/${uuid}/${s}.json`;
  console.log(`${s} -> ${url}`);
  return url;
}

function oneStarHeaders() {
  result = [];
  for (let i = 1; i <= maxDays(); i++)
  {
    result.push({
      "headerName": `${i}/*->**`,
      "headerTooltip": `Dec ${i} *->**`,
      "field": `d${i}`});
  }
  return result;
}

function twoStarHeaders() {
  result = [];
  for (let day = 1; day <= maxDays(); day++)
  {
    for (let star = 0; star < 2; star++)
    result.push({
      "headerName": `${day}/${star+1}`,
      "headerTooltip": `Dec ${day} *${star+1}`,
      "field": `d${day}_${star}`});
  }
  return result;
}

const default_coldefs_two_stars = {
  "sortable": true,
  "width": 70,
  "comparator": comparator,
  "cellStyle": medalPainter,
  "type": "numericColumn"};

const default_coldefs_two_stars_time = {
  "sortable": true,
  "width": 120,
  "comparator": comparator,
  "cellStyle": medalPainter,
  "type": "numericColumn",
  "valueFormatter": timedelta_to_string};

const default_coldefs_one_stars_time = {
  "sortable": true,
  "width": 120,
  "comparator": comparator,
  "cellStyle": medalPainter_star2,
  "type": "numericColumn",
  "valueFormatter": timedelta_to_string};

const coldefs_default = [
  {
    "field": "name",
    "resizable": true,
    "pinned": "left",
    "width": 200
  },
  {
    "field": "T",
    "width": 70,
    "headerTooltip": "Total score"
  },
  {
    "field": "G",
    "headerTooltip":
    "Global score"
  },
  {
    "field": "S",
    "headerTooltip": "# stars (problems solved)"
  },
  {
    "field": "Tob",
    "headerTooltip":
    "Tobii score"
  }
];

var two_star_coldefs = [...coldefs_default, ...twoStarHeaders()];
var one_star_coldefs = [...coldefs_default, ...oneStarHeaders()];

function globalResults(datakey, config) {
  const grid = config[datakey].opts.api;
  const playersWithGlobalScore = [];

  grid.forEachNode(function(node, index) {
    const data = node.data;
    for (let i = 0; i < data.length; i++) {
      let keys = Object.keys(data[i]);
      for (let j = 5; j < keys.length; j++) {
        key = keys[j]
        if (data[i][key] > 0) {
          console.log(data[i].name);
          playersWithGlobalScore.push(data[i].name.split(".")[1] + "(" + key + ")");
        };
      }
    }
  });

  const el = document.querySelector("#global_result");
  if (!el) return;
  if (playersWithGlobalScore.length == 0) {
    el.innerHTML = "<br>Maybe tomorrow someone will be in the global top 100... Good luck :)";
  } else {
    el.innerHTML = "<br>Congratulations " + playersWithGlobalScore.join() + "!";
  }
}

function fillData(rows) {
    var data = new google.visualization.DataTable();
    // Why is this line required??
    data.addColumn('number', 'X');
    for (let i = 0; i < all_players.length; i++) {
        data.addColumn('number', all_players[i]);
    }
    data.addRows(rows);
    return data;
};

function drawChart(elementId, rows, opts) {
    const options = {
        width: $('#tabmenu').width(),
        height: 1000,
        left: 20,
        top: 20,
        hAxis: { title: 'day/star' },
        explorer: {zoomDelta: 1.1},
        ...opts
    };
    const chart = new google.visualization.LineChart(document.getElementById(elementId));
    chart.draw(fillData(rows), options);
}

function stylePosMedals(player, column, medal_data) {
    // Is this a medal-cell?
    const c = medal_data[column];
    if (!c) {
      return;
    }

    const medal = c[player];
    if (medal) {
        return medal_css[medal];
    }
}

function zpad(s) {
    return ("00" + s.toString()).slice(-2);
}

function astime(data) {
    let n = parseInt(data, 0);

    if (n == 0) {
        return "Winner";
    }

    if (!(n)) {
        return data;
    }

    const SECSINMIN = 60;
    const SECSINHOUR = SECSINMIN * 60;
    const HOURSINDAY = 24;
    const SECSINDAY = HOURSINDAY * SECSINHOUR;

    const days = zpad((n / SECSINDAY) >> 0);
    n = n % SECSINDAY;
    const hours = zpad((n / SECSINHOUR) >> 0);
    n = n % SECSINHOUR;
    const minutes = zpad((n / SECSINMIN) >> 0)

    const seconds = zpad(n % SECSINMIN);

    if (days != "00") {
        return `${days}.${hours}:${minutes}:${seconds}`;
    };
    return `${hours}:${minutes}:${seconds}`;
};

function getColumnIndex(params) {
  const colId = params.column.colId;
  const columns = params.columnApi.columnController.columnDefs;
  for (let i = 0; i < columns.length; i++) {
      if (columns[i].field == colId) {
          return i;
      }
  }
  return 0;
}

function timedelta_to_string(params) {
    if (getColumnIndex(params) < 5) {
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
  for (let i = 0; i < columns.length; i++) {
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
  const colIndex = getSortColumn(nodeA.columnApi.getColumnState());

  const k = Object.keys(nodeA.data)[colIndex];

  if (colIndex==0) { // Name
    return sortString(nodeA.data[k], nodeB.data[k]);
  }

  // Map null -> [ten years into the future] to make those values sort last
  const tenYears = 10 * 365 * 24 * 3600;
  const v1 = (nodeA.data[k] == null) ? tenYears : nodeA.data[k];
  const v2 = (nodeB.data[k] == null) ? tenYears : nodeB.data[k];
  return v1 - v2;
}

function restoreTab() {
  const urlParams = new URLSearchParams(window.location.search);
  const tab = urlParams.get('tab') || "sectionLeaderboard";
  const buttonId = `btn_${tab.slice("section".length)}`;
  const button =  document.getElementById(buttonId);

  if (button) {
    openTab(button, tab, charts);
  }
}

function updateTimeFetched(datakey, firstTime) {
  const timeFetchedTextHolder = document.getElementById(`fetchtime${datakey}`);
  if (!timeFetchedTextHolder) return;
  const d = new Date();
  timeFetchedTextHolder.innerText = `Retrieved from server @ ${d}`

  if (!firstTime) {
    const aocFetchedTextHolder = document.getElementById(`aocTime${datakey}`);
    aocFetchedTextHolder.innerText += "+";
  }
}

function fetchTableData(datakey, config, opts) {
  console.log("loading data for ", datakey);

  const widgetConfig = config[datakey];
  const url = makeUrl(widgetConfig.dataname);
  const api = widgetConfig.opts.api;
  return fetch(url)
    .then(response => response.json())
    .then(data => api.setRowData(data))
    .then(() => {
      const filterInstance = api.getFilterInstance("T");
      filterInstance.setModel({
        filterType: 'number',
        type: 'notEqual',
        filter: '0'
      });
      api.onFilterChanged();
      filters.push(datakey);
    })
    .then(() => updateTimeFetched(datakey, opts.firstTime));
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

  // This line doesn't seem to do anything useful in local state.
  // window.history.pushState({},
  //   "",
  //   document.location.origin + document.location.pathname + "?tab=" + tabName);

  // Show requested tab and set red status indicator
  const tab = document.getElementById(tabName);
  if (tab) tab.style.display = "block";
  target.className += " w3-red";
  const datatype = target.attributes.datatype ? target.attributes.datatype.value : undefined
  const datakey = target.attributes.datakey ? target.attributes.datakey.value : undefined
  console.log(`${datatype}: ${datakey}`)

  if (generated.includes(datakey)) {
    console.log("Using pregenerated widget")
    return;
  };
  generated.push(datakey);
  const widgetConfig = config[datakey];

  let widgetPromise;
  if (datatype == "table") {
    new agGrid.Grid(
      document.querySelector(`#table${datakey}`),
      widgetConfig.opts);

    widgetPromise = fetchTableData(datakey, config, {firstTime: true});
  } else if (datatype == "chart") {
    const url = makeUrl(widgetConfig.dataname);
    console.log(`${datakey} <- ${url}`);
    widgetPromise = fetch(url)
      .then(response => response.json())
      .then(data => drawChart(
        `chart${datakey}`,
        data,
        widgetConfig.opts));
  } else {
    console.warn("Unknown type: ", datatype);
  }
  if (widgetPromise && widgetConfig.configFunction) {
    widgetPromise.then(() => widgetConfig.configFunction(datakey, config));
  }
};

var filters = [];

function switchFilter(chart) {
  const api = charts[chart].opts.api
  const filterInstance = api.getFilterInstance("T");
  const button = document.getElementById(`filter${chart}`);
  if (filters.includes(chart)) {
    filters = filters.filter(function(value, index, arr){
      return value != chart;
    });
    var filter = null
    button.innerText = "Hide inactive";
  }
  else {
    filters.push(chart);
    var filter = {
      filterType: 'number',
      type: 'notEqual',
      filter: '0'
    };
    button.innerText = "Show inactive";
  }
  filterInstance.setModel(filter);
  api.onFilterChanged();
  console.log(filters);
}

function createMenu(config) {
    // var menu = document.getElementById("tabmenu");
    console.log($("#tabmenu"));
    for (const chart in charts) {
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
          <p>${document.title}</p>
          <h1>${config[chart].header}</h1>
          <p>${config[chart].desc}</p>
          <div class="chart" id="chart${chart}"></div>
          <p align="right">Data fetched from AoC @ ${charts.generatedTime}.</p>
          </div>
          `);
        } else {
          $("#tables").append(`
          <div id="section${chart}" class="w3-container w3-border tab" style="display:none; height: 100%">
          <p>${document.title}</p>
          <h1>${config[chart].header}</h1>
          <button id="filter${chart}" onclick="switchFilter('${chart}')">Show inactive</button>
          <button id="refetch${chart}" onclick="fetchTableData('${chart}', charts, {firstTime: false})">Refetch</button>
          <p>${config[chart].desc}</p>
          <div id="table${chart}" style="width: auto;" class="ag-theme-alpine"></div>
          <p align="right" id="aocTime${chart}">Data fetched from AoC @ ${charts.generatedTime}.</p>
          <p align="right" id="fetchtime${chart}"/>
        </div>
        `);
      }
    }
}

const charts = {
  "Leaderboard": {
    buttonText: "Leaderboard",
    header: "Leaderboard/Local score (pos)",
    desc: `Initially sorted by position in the list.
          The number for each problem show the player's position after completing the problem.
          Medals are awarded to the fastest players.
          Blank cells indicate the player did not yet solve that particular challenge.`,
    opts: {
      columnDefs: two_star_coldefs,
      domLayout: 'autoHeight',
      defaultColDef: default_coldefs_two_stars,
    },
    dataname: "table-dailyposition"
  },
  "PositionChart": {
    isChart: true,
    buttonText: "Position Chart",
    header: "Positions evolving over time",
    desc: "",
    opts: {vAxis: { logScale: 'False', title: 'Daily Position' }},
    dataname: "graph-accumulated_position_graph"
  },
  "LeaderboardScore": {
    buttonText: "Leaderboard (score)",
    header: "Leaderboard/Local score (accumulated score)",
    desc: `Initially sorted by position in the list.
          The number for each problem show the player's total score after completing the problem.
          Medals are awarded to the fastest players.`,
    opts: {
      columnDefs: two_star_coldefs,
      domLayout: 'autoHeight',
      defaultColDef: default_coldefs_two_stars,
    },
    dataname: "table-accumulated_score"
  },
  "Time": {
    buttonText: "Time",
    header: "Time to complete problem after release",
    desc: `Initially sorted by position in the list.
          The time it took for the players to complete the problem after its release.
          Format is &lt;days&gt;.hours:minutes:seconds.
          Medals are awarded to the fastest players.`,
    opts: {
      columnDefs: two_star_coldefs,
      domLayout: 'autoHeight',
      defaultColDef: default_coldefs_two_stars_time,
    },
    dataname: "table-time_to_complete"
  },
  "Offset": {
    buttonText: "Offset",
    header: "Offset from winning player",
    desc: `Initially sorted by position in the list.
          Table shows how long after the fastest player the rest completed the challenge.
          Format is &lt;days&gt;.hours:minutes:seconds.
          Medals are awarded to the fastest players.`,
    opts: {
      columnDefs: two_star_coldefs,
      domLayout: 'autoHeight',
      defaultColDef: default_coldefs_two_stars_time,
    },
    dataname: "table-offset_from_winner"
  },
  "Accumulatedtime": {
    buttonText: "Accumulated time",
    header: "Accumulated time to solve",
    desc: `Yadayada`,
    opts: {
      columnDefs: two_star_coldefs,
      domLayout: 'autoHeight',
      defaultColDef: default_coldefs_two_stars_time,
    },
    dataname: "table-accumulated_solve_time"
  },
  "Timestar2": {
    buttonText: "Time star2",
    header: "Time to complete second problem",
    desc: `Initially sorted by position in the list.
          Table shows how long time it took to solve the second problem efter completing the first.
          Format is &lt;days&gt;.hours:minutes:seconds.
          Medals are awarded to the players with the shortest time between star 1 and star 2.`,
    opts: {
      columnDefs: one_star_coldefs,
      domLayout: 'autoHeight',
      defaultColDef: default_coldefs_one_stars_time,
    },
    dataname: "table-time_to_second_star"
  },
  "scoreDiff": {
    buttonText: "Score diff",
    header: "Points behind the leader",
    desc: `Initially sorted by position in the list.
          Table shows how far behind the leader players are.
          Medals are awarded to the fastest players.`,
    opts: {
      columnDefs: two_star_coldefs,
      domLayout: 'autoHeight',
      defaultColDef: default_coldefs_two_stars,
    },
    dataname: "table-score_diff"
  },
  "Score diff Chart": {
    isChart: true,
    buttonText: "Score diff Chart",
    header: "",
    desc: "",
    opts: {vAxis: { logScale: 'True', title: 'Points behind the leader' }},
    dataname: "graph-scorediff_graph"
  },
  "globalScore": {
    buttonText: "Global score",
    header: "Global score",
    desc: `Initially sorted by position in the list.
          Table shows how many global scores were achieved on a daily basis.
          Medals are awarded to the fastest players.
          <br>
          <span id="global_result">
          `,
    opts: {
      columnDefs: two_star_coldefs,
      domLayout: 'autoHeight',
      defaultColDef: default_coldefs_two_stars,
    },
    dataname: "table-global_score",
    configFunction: (datakey, config) => globalResults(datakey, config)
  },
  "dailyPosition": {
    buttonText: "Daily position",
    header: "Daily position",
    desc: `Initially sorted by position in the list.
          Table shows the position each player achieved per problem.
          Medals are awarded to the fastest players.`,
    opts: {
      columnDefs: two_star_coldefs,
      domLayout: 'autoHeight',
      defaultColDef: default_coldefs_two_stars,
    },
    dataname: "table-accumulated_position",
  },
  "Daily position Chart": {
    isChart: true,
    buttonText: "Daily position Chart",
    header: "",
    desc: "",
    opts: {vAxis: { logScale: 'False', title: 'Position' }},
    dataname: "graph-daily_position_graph"
  },
  "tobiiScore": {
    buttonText: "Tobii Score",
    header: "Tobii score",
    desc: `Initially sorted by position in the list.
          ...tobii score explanation.
          Medals are awarded to the fastest players.`,
    opts: {
      columnDefs: two_star_coldefs,
      domLayout: 'autoHeight',
      defaultColDef: default_coldefs_two_stars,
    },
    dataname: "table-global_score",
  },
}

function handleError(err) {
  el = document.getElementById("error");
  el.innerText = "Unable to find the requested page. Wrong guid? Wrong year?";
}

function handleParams()
{
  const params = new URLSearchParams(window.location.search)
  const now = new Date();
  let defaultYear = now.getFullYear().toString();
  if (now.getMonth() != 11) {
    defaultYear = (now.getFullYear() - 1).toString();
  }

  year=params.get("year") || defaultYear
  uuid = params.get("uuid") || "21ae6a02-ec22-469e-ae39-c63e921b309b";
  console.log("params:", year, uuid);
}

window.onload = function() {
  handleParams();

  fetch(makeUrl("var-config"))
    .then(response => response.json())
    .then(data => {
        document.title = `${data["title"]} - ${year}`;
        all_players = data["all_players"];
        medals_best_times = data["medals_best_time"];
        medals_star2 = data["medals_star2"];
        charts.generatedTime = data.extravars.generated
      })
    .then(() => {
        createMenu(charts);
        restoreTab();
      })
    .catch(err => handleError(err));
}