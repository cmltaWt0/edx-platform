# Theming constants
THEME_NAME = ENV_TOKENS['THEME_NAME']
USE_CUSTOM_THEME = !(THEME_NAME.nil? || THEME_NAME.empty?)
if USE_CUSTOM_THEME
    THEME_ROOT = File.join(ENV_ROOT, "themes", THEME_NAME)
    THEME_SASS = File.join(THEME_ROOT, "static", "sass")
end

# Run the specified file through the Mako templating engine, providing
# the ENV_TOKENS to the templating context.
def preprocess_with_mako(filename)
    # simple command-line invocation of Mako engine
    mako = "from mako.template import Template;" +
           "print Template(filename=\"#{filename}\")" +
           # Total hack. It works because a Python dict literal has
           # the same format as a JSON object.
           ".render(env=#{ENV_TOKENS.to_json.gsub("true","True").gsub("false","False")});"

    # strip off the .mako extension
    output_filename = filename.chomp(File.extname(filename))

    # just pipe from stdout into the new file, exiting on failure
    File.open(output_filename, 'w') do |file|
      file.write(`python -c '#{mako}'`)
      exit_code = $?.to_i
      abort "#{mako} failed with #{exit_code}" if exit_code.to_i != 0
    end
end

def xmodule_cmd(watch=false, debug=false)
    xmodule_cmd = 'xmodule_assets common/static/xmodule'
    if watch
        "watchmedo shell-command " +
                   "--patterns='*.js;*.coffee;*.sass;*.scss;*.css' " +
                   "--recursive " +
                   "--command='#{xmodule_cmd}' " +
                   "common/lib/xmodule"
    else
        xmodule_cmd
    end
end

def coffee_cmd(watch=false, debug=false)
    if watch
        # On OSx, coffee fails with EMFILE when
        # trying to watch all of our coffee files at the same
        # time.
        #
        # Ref: https://github.com/joyent/node/issues/2479
        #
        # Instead, watch 50 files per process in parallel
        cmds = []
        Dir['*/static/**/*.coffee'].each_slice(50) do |coffee_files|
            cmds << "node_modules/.bin/coffee --watch --compile #{coffee_files.join(' ')}"
        end
        cmds
    else
        'node_modules/.bin/coffee --compile */static'
    end
end

def sass_cmd(watch=false, debug=false)
    sass_load_paths = ["./common/static/sass"]
    sass_watch_paths = ["*/static"]
    if USE_CUSTOM_THEME
      sass_load_paths << THEME_SASS
      sass_watch_paths << THEME_SASS
    end

    "sass #{debug ? '--debug-info' : '--style compressed'} " +
          "--load-path #{sass_load_paths.join(' ')} " +
          "--require ./common/static/sass/bourbon/lib/bourbon.rb " +
          "#{watch ? '--watch' : '--update'} #{sass_watch_paths.join(' ')}"
end

desc "Compile all assets"
multitask :assets => 'assets:all'

namespace :assets do

    desc "Compile all assets in debug mode"
    multitask :debug

    desc "Preprocess all static assets that have the .mako extension"
    task :preprocess do
      # Run assets through the Mako templating engine. Right now we
      # just hardcode the asset filenames.
      preprocess_with_mako("lms/static/sass/application.scss.mako")
    end

    desc "Watch all assets for changes and automatically recompile"
    task :watch => 'assets:_watch' do
        puts "Press ENTER to terminate".red
        $stdin.gets
    end

    {:xmodule => :install_python_prereqs,
     :coffee => :install_node_prereqs,
     :sass => [:install_ruby_prereqs, :preprocess]}.each_pair do |asset_type, prereq_tasks|
        desc "Compile all #{asset_type} assets"
        task asset_type => prereq_tasks do
            cmd = send(asset_type.to_s + "_cmd", watch=false, debug=false)
            if cmd.kind_of?(Array)
                cmd.each {|c| sh(c)}
            else
                sh(cmd)
            end
        end

        multitask :all => asset_type
        multitask :debug => "assets:#{asset_type}:debug"
        multitask :_watch => "assets:#{asset_type}:_watch"

        namespace asset_type do
            desc "Compile all #{asset_type} assets in debug mode"
            task :debug => prereq_tasks do
                cmd = send(asset_type.to_s + "_cmd", watch=false, debug=true)
                sh(cmd)
            end

            desc "Watch all #{asset_type} assets and compile on change"
            task :watch => "assets:#{asset_type}:_watch" do
                puts "Press ENTER to terminate".red
                $stdin.gets
            end

            task :_watch => prereq_tasks do
                cmd = send(asset_type.to_s + "_cmd", watch=true, debug=true)
                if cmd.kind_of?(Array)
                    cmd.each {|c| background_process(c)}
                else
                    background_process(cmd)
                end
            end
        end
    end


    multitask :sass => 'assets:xmodule'
    namespace :sass do
        # In watch mode, sass doesn't immediately compile out of date files,
        # so force a recompile first
        task :_watch => 'assets:sass:debug'
        multitask :debug => 'assets:xmodule:debug'
    end

    multitask :coffee => 'assets:xmodule'
    namespace :coffee do
        multitask :debug => 'assets:xmodule:debug'
    end
end

[:lms, :cms].each do |system|
    # Per environment tasks
    environments(system).each do |env|
        desc "Compile coffeescript and sass, and then run collectstatic in the specified environment"
        task "#{system}:gather_assets:#{env}" => :assets do
            sh("#{django_admin(system, env, 'collectstatic', '--noinput')} > /dev/null") do |ok, status|
                if !ok
                    abort "collectstatic failed!"
                end
            end
        end
    end
end
